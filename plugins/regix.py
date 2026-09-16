import os
import sys 
import math
import time
import asyncio 
import logging
from .utils import STS
from database import db 
from .test import CLIENT , start_clone_bot
from config import Config, temp
from translation import Translation
from pyrogram import Client, filters 
#from pyropatch.utils import unpack_new_file_id
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Translation.TEXT1

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user = message.from_user.id
    temp.CANCEL[user] = False
    parts = message.data.split("_", 2)
    if len(parts) < 3:
        return await message.answer("Invalid forwarding request.", show_alert=True)
    frwd_id = parts[2]
    if temp.lock.get(user) and str(temp.lock.get(user)) == "True":
        return await message.answer("please wait until previous task complete", show_alert=True)
    sts = STS(frwd_id)
    if not sts.verify():
        await sts.load()
    if not sts.verify():
        await message.answer("your are clicking on my old button", show_alert=True)
        return await message.message.delete()
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT or temp.lock.get(user):
        return await message.answer("In Target chat a task is progressing. please wait until task complete", show_alert=True)

    temp.lock[user] = True
    try:
        await message.message.edit("<b>Starting forwarding...</b>", reply_markup=None)
    except Exception:
        pass

    task = asyncio.create_task(run_forwarding(bot, user, frwd_id, message.message, sts, resume=False))
    temp.FORWARD_TASKS[user] = task
    return await message.answer()


async def run_forwarding(bot, user, frwd_id, m, sts, resume=False):
    """Run a forwarding job, optionally restoring it after a bot restart."""
    temp.CANCEL[user] = False
    i = sts.get(full=True)
    _bot, caption, forward_tag, data, protect, button = await sts.get_data(user, sts.get("account_id"))
    disabled_filters = set(data.get('filters') or [])
    keywords = [str(x).lower() for x in (data.get('keywords') or []) if str(x).strip()]
    extensions = [str(x).lower().lstrip('.') for x in (data.get('extensions') or []) if str(x).strip()]
    media_size = data.get('media_size')
    skip_duplicate = bool(data.get('skip_duplicate'))
    seen_media = set()

    if not _bot:
        if not resume:
            return await msg_edit(m, "<b>You didn't added any bot. Please add a bot using /settings !</b>", wait=True)
        await db.rmve_frwd(user)
        return

    try:
        account_id = sts.get("account_id") or _bot.get("id")
        client = await start_clone_bot(CLIENT.client(_bot, name=f"FORWARD_{user}_{account_id}"))
    except Exception as e:
        logger.exception("Unable to start forwarding client")
        temp.lock[user] = False
        temp.FORWARD_TASKS.pop(user, None)
        if not resume:
            return await msg_edit(m, f"<b>Unable to start forwarding client.</b>", wait=True)
        return

    try:
        # On a fresh start this is the normal verification flow. On resume the
        # old progress message is kept intact and only its progress is edited.
        if not resume:
            await send(client, user, Translation.FORWARDING_STARTED)
            await msg_edit(m, "<b>verifying your data's, please wait..</b>")
            try:
                await client.get_messages(sts.get("FROM"), sts.get("limit"))
            except Exception:
                await msg_edit(m, f"**Source chat may be a private channel / group. Use userbot (user must be member over there) or if Make Your [Bot](t.me/{_bot['username']}) an admin over there**", retry_btn(frwd_id), True)
                return await stop(client, user, remove_job=True)
            try:
                k = await client.send_message(i.TO, "Testing")
                await k.delete()
            except Exception:
                await msg_edit(m, f"**Please Make Your [UserBot / Bot](t.me/{_bot['username']}) Admin In Target Channel With Full Permissions**", retry_btn(frwd_id), True)
                return await stop(client, user, remove_job=True)
            temp.forwardings += 1
            temp.IS_FRWD_CHAT.append(i.TO)
            temp.lock[user] = True
            sts.add(time=True)
            # Store the exact existing progress message so restart can reuse it.
            await db.add_frwd(user, frwd_id, {
                'message_id': m.id,
                'message_chat_id': user,
                'state': dict(sts.data[sts.id]),
            })
            await msg_edit(m, "<b>Processing...</b>")
        else:
            # Recreate only the in-memory state needed by the existing status UI.
            temp.forwardings += 1
            if i.TO not in temp.IS_FRWD_CHAT:
                temp.IS_FRWD_CHAT.append(i.TO)
            temp.lock[user] = True
            await msg_edit(m, "<b>Processing...</b>")

        sleep = 1 if _bot['is_bot'] else 10
        MSG = []
        pling = 0
        await edit(m, 'Progressing', 10, sts)
        total = int(sts.get('total') or 0)
        fetched = int(sts.get('fetched') or 0)
        remaining = max(0, total - fetched)
        if remaining <= 0:
            await finish_job(client, user, m, sts)
            return

        source_chat = sts.get('FROM')
        start_id = int(sts.get('skip') or 0) + 1
        end_id = int(sts.get('limit') or 0)
        batch_size = 100

        # Read the exact message-id range directly. This avoids Pyrogram's
        # iterator getting stuck on very large Telegram message IDs.
        for batch_start in range(start_id, end_id + 1, batch_size):
            if await is_cancelled(client, user, m, sts):
                return

            batch_end = min(batch_start + batch_size - 1, end_id)
            message_ids = list(range(batch_start, batch_end + 1))

            try:
                messages = await asyncio.wait_for(
                    client.get_messages(source_chat, message_ids),
                    timeout=30
                )
            except asyncio.TimeoutError:
                if await is_cancelled(client, user, m, sts):
                    return
                await msg_edit(m, "<b>Telegram is taking too long to read the source messages. Retrying...</b>")
                try:
                    messages = await asyncio.wait_for(
                        client.get_messages(source_chat, message_ids),
                        timeout=30
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError("Timed out while reading source messages")

            if not isinstance(messages, (list, tuple)):
                messages = [messages]

            for message in messages:
                if await is_cancelled(client, user, m, sts):
                    return

                pling += 1
                sts.add('fetched')
                await sts.persist(user)

                if message is None or getattr(message, 'empty', False) or getattr(message, 'service', False):
                    sts.add('deleted')
                    await sts.persist(user)
                    continue

                if not should_forward_message(message, disabled_filters, keywords=keywords,
                                              extensions=extensions, media_size=media_size):
                    sts.add('filtered')
                    await sts.persist(user)
                    continue

                if skip_duplicate:
                    file_id = get_message_file_id(message)
                    if file_id:
                        if file_id in seen_media:
                            sts.add('duplicate')
                            await sts.persist(user)
                            continue
                        seen_media.add(file_id)

                if forward_tag:
                    MSG.append(message.id)
                    remaining_to_process = sts.get('total') - sts.get('fetched')
                    if len(MSG) >= 100 or remaining_to_process <= 100:
                        await forward(client, MSG, m, sts, protect)
                        sts.add('total_files', len(MSG))
                        await sts.persist(user)
                        MSG = []
                else:
                    new_caption = custom_caption(message, caption)
                    details = {
                        "msg_id": message.id,
                        "media": media(message),
                        "caption": new_caption,
                        'button': button,
                        "protect": protect
                    }
                    await copy(client, details, m, sts)
                    sts.add('total_files')
                    await sts.persist(user)
                    await asyncio.sleep(sleep)

                if pling % 10 == 0 or sts.get('fetched') == sts.get('total'):
                    await edit(m, 'Progressing', 10, sts)

        if MSG:
            await forward(client, MSG, m, sts, protect)
            sts.add('total_files', len(MSG))
            await sts.persist(user)
        await finish_job(client, user, m, sts)
    except asyncio.CancelledError:
        temp.CANCEL[user] = True
        try:
            await edit(m, "Cancelled", "cancelled", sts)
        except Exception:
            pass
        try:
            await send(client, user, "<b>❌ Forwarding Process Cancelled</b>")
        except Exception:
            pass
        await stop(client, user, remove_job=True)
        raise
    except Exception:
        logger.exception("Forwarding job failed for user %s", user)
        await safe_edit_progress(m, sts)
        await stop(client, user, remove_job=False)
    finally:
        task = temp.FORWARD_TASKS.get(user)
        if task is asyncio.current_task():
            temp.FORWARD_TASKS.pop(user, None)


async def resume_forwardings(bot):
    """Restore persisted jobs after startup without sending restart messages."""
    cursor = await db.get_all_frwd()
    async for job in cursor:
        try:
            user = int(job['user_id'])
            frwd_id = str(job.get('forward_id') or '')
            state = job.get('state') or {}
            message_id = job.get('message_id')
            message_chat_id = job.get('message_chat_id', user)
            if not frwd_id or not message_id or not state:
                # Old records from the pre-resume version cannot be safely resumed.
                await db.rmve_frwd(user)
                continue
            sts = STS(frwd_id)
            sts.data[frwd_id] = state
            sts.get(full=True)
            try:
                m = await bot.get_messages(message_chat_id, int(message_id))
            except Exception:
                await db.rmve_frwd(user)
                continue
            if not m:
                await db.rmve_frwd(user)
                continue
            if temp.lock.get(user):
                continue
            asyncio.create_task(run_forwarding(bot, user, frwd_id, m, sts, resume=True))
        except Exception:
            logger.exception("Could not restore a forwarding job")


async def safe_edit_progress(m, sts):
    try:
        await edit(m, 'Progressing', 10, sts)
    except Exception:
        pass


async def finish_job(client, user, m, sts):
    try:
        if sts.TO in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.TO)
    except ValueError:
        pass
    except Exception:
        pass
    await send(client, user, "<b>🎉 ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>")
    await edit(m, 'Completed', "completed", sts)
    await stop(client, user, remove_job=True)

async def copy(bot, msg, m, sts):
   try:                                  
     if msg.get("media") and msg.get("caption"):
        await bot.send_cached_media(
              chat_id=sts.get('TO'),
              file_id=msg.get("media"),
              caption=msg.get("caption"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
     else:
        await bot.copy_message(
              chat_id=sts.get('TO'),
              from_chat_id=sts.get('FROM'),    
              caption=msg.get("caption"),
              message_id=msg.get("msg_id"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
   except FloodWait as e:
     await edit(m, 'Progressing', e.value, sts)
     await asyncio.sleep(e.value)
     await edit(m, 'Progressing', 10, sts)
     await copy(bot, msg, m, sts)
   except Exception as e:
     print(e)
     sts.add('deleted')
        
async def forward(bot, msg, m, sts, protect):
   try:                             
     await bot.forward_messages(
           chat_id=sts.get('TO'),
           from_chat_id=sts.get('FROM'), 
           protect_content=protect,
           message_ids=msg)
   except FloodWait as e:
     await edit(m, 'Progressing', e.value, sts)
     await asyncio.sleep(e.value)
     await edit(m, 'Progressing', 10, sts)
     await forward(bot, msg, m, sts, protect)

PROGRESS = """
📈 Percetage: {0} %

♻️ Feched: {1}

♻️ Fowarded: {2}

♻️ Remaining: {3}

♻️ Stataus: {4}

⏳️ ETA: {5}

My Developer @Mr_Jisshu
"""

async def msg_edit(msg, text, button=None, wait=None):
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        pass 
    except FloodWait as e:
        if wait:
           await asyncio.sleep(e.value)
           return await msg_edit(msg, text, button, wait)
        
async def edit(msg, title, status, sts):
   i = sts.get(full=True)
   status = 'Forwarding' if status == 10 else f"Sleeping {status} s" if str(status).isnumeric() else status
   percentage = "{:.0f}".format(float(i.fetched)*100/float(i.total)) if int(i.total or 0) > 0 else "100"
   
   now = time.time()
   diff = int(now - i.start)
   speed = sts.divide(i.fetched, diff)
   elapsed_time = round(diff) * 1000
   time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000
   estimated_total_time = elapsed_time + time_to_completion  
   progress = "▰{0}{1}".format(
       ''.join(["▰" for i in range(math.floor(int(percentage) * 15/ 100))]),
       ''.join(["▱" for i in range(15 - math.floor(int(percentage) * 15 / 100))]))
   button = [[InlineKeyboardButton(f'{progress}', callback_data=f'fwrdstatus#{status}#{estimated_total_time}#{percentage}#{i.id}')]]
   estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
   estimated_total_time = estimated_total_time if estimated_total_time != '' else '0 s'

   text = TEXT.format(i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, status, percentage, estimated_total_time, status)
   if status in ["cancelled", "completed"]:
      button.append(
         [InlineKeyboardButton('Support', url='https://t.me/Jisshu_support'),
         InlineKeyboardButton('Updates', url='https://t.me/jisshubots')]
         )
   else:
      button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
   await msg_edit(msg, text, InlineKeyboardMarkup(button))
   
async def is_cancelled(client, user, msg, sts):
   if temp.CANCEL.get(user) == True:
      try:
         if sts.TO in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.TO)
      except (ValueError, AttributeError):
         pass
      await edit(msg, "Cancelled", "cancelled", sts)
      await send(client, user, "<b>❌ Forwarding Process Cancelled</b>")
      await stop(client, user, remove_job=True)
      return True
   return False

async def stop(client, user, remove_job=True):
   try:
      await client.stop()
   except Exception:
      pass
   if remove_job:
      await db.rmve_frwd(user)
   try:
      if temp.forwardings > 0:
         temp.forwardings -= 1
   except Exception:
      pass
   temp.lock[user] = False

async def send(bot, user, text):
   try:
      await bot.send_message(user, text=text)
   except:
      pass 
     
def message_type(msg):
  """Return the setting key corresponding to a Telegram message."""
  if getattr(msg, "poll", None):
    return "poll"
  for key in ("text", "document", "video", "photo", "audio",
              "voice", "animation", "sticker"):
    if getattr(msg, key, None) is not None:
      return key
  return None


def get_message_file_id(msg):
  """Return a stable Telegram file id for duplicate detection."""
  for key in ("document", "video", "photo", "audio", "voice",
              "animation", "sticker"):
    obj = getattr(msg, key, None)
    if obj is None:
      continue
    if key == "photo" and isinstance(obj, (list, tuple)):
      obj = obj[-1] if obj else None
    file_id = getattr(obj, "file_unique_id", None) or getattr(obj, "file_id", None)
    if file_id:
      return file_id
  return None


def should_forward_message(msg, disabled_filters, keywords=None,
                           extensions=None, media_size=None):
  """
  Check every forwarding filter.
  disabled_filters contains keys that are OFF in Settings.
  """
  msg_type = message_type(msg)

  # Known message types are controlled by the matching toggle.
  if msg_type in disabled_filters:
    return False

  # If a media type is configured but Telegram returned an unknown type,
  # don't accidentally treat it as an enabled file type.
  if msg_type is None:
    return False

  # Keyword/extension/size settings apply to files/media with a filename.
  media_obj = None
  for key in ("document", "video", "audio", "voice", "animation", "photo"):
    obj = getattr(msg, key, None)
    if obj is not None:
      if key == "photo" and isinstance(obj, (list, tuple)):
        obj = obj[-1] if obj else None
      media_obj = obj
      break

  if media_obj is not None:
    file_name = str(getattr(media_obj, "file_name", "") or "")
    lower_name = file_name.lower()

    if keywords and not any(word in lower_name for word in keywords):
      return False

    if extensions:
      ext = lower_name.rsplit(".", 1)[-1] if "." in lower_name else ""
      if ext in extensions:
        return False

    if media_size and getattr(media_obj, "file_size", None) is not None:
      limit_mb, mode = media_size
      try:
        limit_bytes = float(limit_mb) * 1024 * 1024
        size_bytes = float(media_obj.file_size)
        if mode is True and size_bytes <= limit_bytes:
          return False
        if mode is False and size_bytes >= limit_bytes:
          return False
        if mode is None and size_bytes != limit_bytes:
          return False
      except (TypeError, ValueError):
        pass

  return True


def custom_caption(msg, caption):
  if msg.media:
    if (msg.video or msg.document or msg.audio or msg.photo):
      media = getattr(msg, msg.media.value, None)
      if media:
        file_name = getattr(media, 'file_name', '')
        file_size = getattr(media, 'file_size', '')
        fcaption = getattr(msg, 'caption', '')
        if fcaption:
          fcaption = fcaption.html
        if caption:
          return caption.format(filename=file_name, size=get_size(file_size), caption=fcaption)
        return fcaption
  return None

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

def media(msg):
  if msg.media:
     media = getattr(msg, msg.media.value, None)
     if media:
        return getattr(media, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', f"start_public_{id}")]])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id
    temp.CANCEL[user_id] = True
    await m.answer("Cancelling forwarding...", show_alert=False)
    task = temp.FORWARD_TASKS.get(user_id)
    if task and not task.done():
        task.cancel()
          
@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    try:
       parts = msg.data.split("#")
       if len(parts) != 5:
          return await msg.answer("Status is temporarily unavailable.", show_alert=True)
       _, status, est_time, percentage, frwd_id = parts
       sts = STS(frwd_id)
       if not sts.verify():
          await sts.load()
       if not sts.verify():
          return await msg.answer("Status is temporarily unavailable.", show_alert=True)
       fetched = int(sts.get('fetched') or 0)
       forwarded = int(sts.get('total_files') or 0)
       remaining = max(0, int(sts.get('total') or fetched) - fetched)
       est_time = TimeFormatter(milliseconds=est_time)
       est_time = est_time if (est_time != '' or status not in ['completed', 'cancelled']) else '0 s'
       return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, est_time), show_alert=True)
    except Exception:
       return await msg.answer("Status is temporarily unavailable.", show_alert=True)
      
@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete()
