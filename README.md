<p align="center">
<img src="https://files.catbox.moe/uevfz8.jpg"/>

<hr>

# FEATURES
 - Forward Messages From Public & Private Channels.
 - Supports Broadcasts.
 - Custom Caption & Buttons.
 - Support Restricted Chats.
 - Skip Duplicate Messages.
 - Message Type Filters.
 - Filter By Extensions, Keywords & File Size.
 - Multiple Source & Target Channels.
 - Forward Videos, Photos, Documents & Other Media.
 - Forwarding Progress & Statistics.
 - MongoDB Database Support.
 - Docker Support.
<details>
 
<summary>More Features</summary>
 
<br>
 
 - Custom Forward Tags.
 - Skip Specific Messages.
 - Cancel Running Forward Tasks.
 - Protected Message Support.
 - Userbot/Pyrogram Session Support.
 - Configurable Forwarding Filters.
 - Duplicate File Detection.
 - Database-Based Message Tracking.

</details>

<hr>

# CONFIGS VARIABLES

Set these variables before starting the bot.

| Variable | Required | Description |
|---|---|---|
| `API_ID` | Yes | Telegram API ID from Telegram |
| `API_HASH` | Yes | Telegram API hash |
| `BOT_TOKEN` | Yes | Bot token from BotFather |
| `BOT_OWNER_ID` | Yes | Admin/owner Telegram user ID(s), separated by spaces |
| `BOT_SESSION` | No | Bot session name. Default: `bot` |
| `PICS` | No | Start/help image URL |
| `DATABASE_URI` | Yes | MongoDB connection URI |
| `DATABASE_NAME` | No | MongoDB database name. Default: `Cluster0` |
| `LOG_CHANNEL` | Yes | Telegram log channel ID |
| `FORCE_SUB_CHANNEL` | Yes* | Force-subscription channel URL/username |
| `FORCE_SUB_ON` | No | Enable/disable force subscription. Default: `True` |

<hr>

# Files

```text
Jisshu-Forward-Bot/
├── Dockerfile
├── Procfile
├── app.json
├── app.py
├── bot.py
├── config.py
├── database.py
├── heroku.yml
├── logging.conf
├── main.py
├── requirements.txt
├── start.sh
├── translation.py
└── plugins/
    ├── broadcast.py
    ├── commands.py
    ├── public.py
    ├── regix.py
    ├── settings.py
    ├── test.py
    ├── unequify.py
    └── utils.py
```

<hr>

# DEPLOYEMENT SUPPORT
## Koyeb

```text
Build:
pip3 install -U -r requirements.txt

Run:
python3 main.py
```

## Render

```text
Build:
pip3 install -U -r requirements.txt

Start:
python3 main.py
```

## VPS

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv

git clone https://github.com/Jisshubot/Jisshu-forward-bot.git
cd Jisshu-forward-bot

python3 -m venv venv
source venv/bin/activate

pip3 install -U -r requirements.txt

python3 main.py
```
<hr>

# ALL COMMANDS

```
start - Start the bot.
forward - Forward messages.
unequify - Delete dublicate files in channel.
settings - Configure your settings.
cancel - Cancel ongoing forwarding.
stats - To check bot stats (Admin Only)
resetall - To reset all user settings. (Admin Only)
broadcast - To broadcast any message to all users (Admin Only)
restart - Restart the bot (Admin Only)
```

## Developer

**ZISHAN / JISSHU BOTS**

<hr>

<p align="center">
  Built with ❤️ by <b>Zishan Khan</b>
</p>

<p align="center">
  📢 <a href="https://t.me/jisshubots">Updates Channel</a>
  &nbsp; • &nbsp;
  💬 <a href="https://t.me/Jisshu_support">Support Group</a>
  &nbsp; • &nbsp;
  👤 <a href="https://t.me/JisshuDeveloperBot">Admin</a>
</p>

<p align="center">
  ⭐ If you find this project useful, don't forget to star the repository!
</p>
