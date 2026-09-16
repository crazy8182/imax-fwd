# bot developer @im_jisshu
import time as tm
from database import db 
from .test import parse_buttons

STATUS = {}

class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS
    
    def verify(self):
        return self.data.get(self.id)

    async def load(self):
        values = await db.nfy.find_one({'forward_id': str(self.id)})
        if not values:
            return False
        values = values.get('state') or values
        values.pop('_id', None)
        values.pop('user_id', None)
        values.pop('forward_id', None)
        self.data[self.id] = values
        self.get(full=True)
        return True

    async def persist(self, user_id):
        values = dict(self.data.get(self.id) or {})
        if not values:
            return
        await db.update_frwd(int(user_id), {
            'forward_id': str(self.id),
            'state': values
        })
    
    def store(self, From, to, skip, limit, account_id=None):
        skip = max(0, int(skip))
        limit = max(skip, int(limit))
        self.data[self.id] = {"FROM": From, 'TO': to, 'total_files': 0, 'skip': skip, 'limit': limit,
                      'fetched': 0, 'filtered': 0, 'deleted': 0, 'duplicate': 0, 'total': max(0, limit - skip), 'start': 0, 'account_id': account_id}
        self.get(full=True)
        return STS(self.id)
        
    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if not full:
           return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def add(self, key=None, value=1, time=False):
        if time:
          return self.data[self.id].update({'start': tm.time()})
        self.data[self.id].update({key: self.get(key) + value}) 
    
    def divide(self, no, by):
       by = 1 if int(by) == 0 else by 
       return int(no) / by 
    
    async def get_data(self, user_id, account_id=None):
        bot = await db.get_bot_by_id(user_id, account_id) if account_id else await db.get_bot(user_id)
        k, filters = self, await db.get_filters(user_id)
        size, configs = None, await db.get_configs(user_id)
        if configs['duplicate']:
           duplicate = [configs['db_uri'], self.TO]
        else:
           duplicate = False
        button = parse_buttons(configs['button'] if configs['button'] else '')
        if configs['file_size'] != 0:
            size = [configs['file_size'], configs['size_limit']]
        return bot, configs['caption'], configs['forward_tag'], {'chat_id': k.FROM, 'limit': k.limit, 'offset': k.skip, 'filters': filters,
                'keywords': configs['keywords'], 'media_size': size, 'extensions': configs['extension'], 'skip_duplicate': duplicate}, configs['protect'], button
        
