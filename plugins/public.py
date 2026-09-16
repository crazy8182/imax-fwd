import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
 
#===================Run Function===================#

@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    accounts = await db.get_bots(user_id)
    if not accounts:
      return await message.reply("<code>You didn't add any bot/userbot. Please add one using /settings !</code>")

    # If multiple accounts are connected, let the user choose which one
    # will perform this forwarding job.
    _bot = accounts[0]
    if len(accounts) > 1:
       account_buttons = []
       account_map = {}
       for account in accounts:
          icon = "🤖" if account.get('is_bot') else "👤"
          username = f"@{account['username']}" if account.get('username') else "private"
          suffix = f" · {account['id']}" if username == "private" else ""
          label = f"{icon} {account['name']} ({username}){suffix}"
          account_buttons.append([KeyboardButton(label)])
          account_map[label] = account['id']
       account_buttons.append([KeyboardButton("cancel")])
       choice = await bot.ask(
          message.chat.id,
          "<b>Choose a bot/userbot to use for forwarding:</b>",
          reply_markup=ReplyKeyboardMarkup(account_buttons, one_time_keyboard=True, resize_keyboard=True)
       )
       if choice.text and choice.text.lower() == "cancel":
          return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
       account_id = account_map.get(choice.text)
       if not account_id:
          return await message.reply_text("Invalid account selected.", reply_markup=ReplyKeyboardRemove())
       _bot = await db.get_bot_by_id(user_id, int(account_id))
       if not _bot:
          return await message.reply_text("Selected account was not found.", reply_markup=ReplyKeyboardRemove())
       account_id = _bot['id']
    else:
       account_id = _bot['id']

    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("please set a to channel in /settings before forwarding")
    if len(channels) > 1:
       for channel in channels:
          buttons.append([KeyboardButton(f"{channel['title']}")])
          btn_data[channel['title']] = channel['chat_id']
       buttons.append([KeyboardButton("cancel")]) 
       _toid = await bot.ask(message.chat.id, Translation.TO_MSG.format(_bot['name'], _bot['username']), reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))
       if _toid.text.startswith(('/', 'cancel')):
          return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
       to_title = _toid.text
       toid = btn_data.get(to_title)
       if not toid:
          return await message.reply_text("wrong channel choosen !", reply_markup=ReplyKeyboardRemove())
    else:
       toid = channels[0]['chat_id']
       to_title = channels[0]['title']
    fromid = await bot.ask(message.chat.id, Translation.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return 
    if fromid.text and not fromid.forward_date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif fromid.forward_from_chat.type in [enums.ChatType.CHANNEL]:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id == None:
           return await message.reply_text("**This may be a forwarded message from a group and sended by anonymous admin. instead of this please send last message link from group**")
    else:
        await message.reply_text("**invalid !**")
        return 
    try:
        title = (await bot.get_chat(chat_id)).title
  #  except ChannelInvalid:
        #return await fromid.reply("**Given source chat is copyrighted channel/group. you can't forward messages from there**")
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')
    skipno = await bot.ask(message.chat.id, Translation.SKIP_MSG)
    if skipno.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return
    try:
        skip_number = int(skipno.text.strip())
        if skip_number < 0:
            raise ValueError
    except (TypeError, ValueError):
        await message.reply_text("<b>Please enter a valid non-negative number.</b>")
        return
    if skip_number > int(last_msg_id):
        await message.reply_text("<b>Skip number cannot be greater than the last message number.</b>")
        return
    forward_id = f"{user_id}-{skipno.id}"
    buttons = [[
        InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
        InlineKeyboardButton('No', callback_data="close_btn")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        text=Translation.DOUBLE_CHECK.format(botname=_bot['name'], botuname=_bot['username'], from_chat=title, to_chat=to_title, skip=skip_number),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, skip_number, int(last_msg_id), account_id=account_id)
