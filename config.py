# bot developer @im_jisshu
from os import environ 

class Config:
    
    API_ID = environ.get("API_ID", "26741021")
    API_HASH = environ.get("API_HASH", "7c5af0b88c33d2f5cce8df5d82eb2a94")
    BOT_TOKEN = environ.get("BOT_TOKEN", "") 
    BOT_OWNER_ID = [int(id) for id in environ.get("BOT_OWNER_ID", '5672857559').split()]
    BOT_SESSION = environ.get("BOT_SESSION", "vegamoviesforwordbot") 

    PICS = (environ.get('PICS', 'https://files.catbox.moe/uevfz8.jpg'))
    
    DATABASE_URI = environ.get("DATABASE_URI", "mongodb+srv://mahesh12:mahesh12@cluster0.hscxg.mongodb.net/?appName=Cluster0")
    DATABASE_NAME = environ.get("DATABASE_NAME", "Cluster0")
    
    LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002084819782'))
    FORCE_SUB_CHANNEL = environ.get("FORCE_SUB_CHANNEL", "https://t.me/imaxmoviehub") # FORCE SUB channel link 
    FORCE_SUB_ON = environ.get("FORCE_SUB_ON", "True")  # FORCE SUB ON - OFF


class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    FORWARD_TASKS = {}
    
