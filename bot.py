from dialog_bot_sdk.bot import DialogBot
from enum import Enum
import grpc
from pymongo import MongoClient
from collections import defaultdict
from dialog_bot_sdk.entities.media.InteractiveMediaGroup import InteractiveMediaStyle
from dialog_bot_sdk.interactive_media import InteractiveMediaGroup, InteractiveMedia, InteractiveMediaSelect, \
    InteractiveMediaConfirm, InteractiveMediaButton
    
class Tables(Enum):
    tokens = 'tokens'
    boards = 'boards'
    lists = 'lists'
    states = 'states'
    query = 'query'
    card_dates = 'card_dates'
    add_text = 'add_text'
    last_card = 'last_card'
    
class States(Enum):
    start = "start"
    add_save = "add_save"
    edit_save = "edit_save"
    comment_save = "comment_save"
    search_results = "search_results"
    
class Sorted(Enum):
    old = 0
    new = 1
    by_name = 2
    
class DBHandler:
    def __init__(self, db_link, db_name):
        self.client = MongoClient(db_link)
        self.db = self.client[db_name]
    
    def get(self, _id, table, field="value"):
        val = self.db[table].find_one({'_id': _id})
        if val and field in val.keys():
            return val[field]
        return val                    
        
    def reset_state(self, _id):
        return self.save(_id, States.start.value, Tables.states.value)
                
    def save(self, uid, value, table, field="value"):
        self.db[table].replace_one({'_id': uid}, {field: value}, upsert=True)
        return value 
    
    def update(self, _id, field, value, table):
        self.db[table].update_one({"_id": _id}, {"$set": {field: value}}) 
        
    def delete(self, _id, table):
        self.db[table].delete_one({'_id': _id})
        

class Strategy:
    def __init__(self, token, endpoint, db_link, db_name, async_=True):
        self.bot = None
        self.endpoint = endpoint
        self.token = token
        self.db_handler = DBHandler(db_link, db_name)
        self.async_ = async_
        
    def start(self, *args, **kwargs):
        self.bot = DialogBot.get_secure_bot(
        self.endpoint,  # bot endpoint (specify different endpoint if you want to connect to your on-premise environment)
        grpc.ssl_channel_credentials(), # SSL credentials (empty by default!)
        self.token,  # bot token
        verbose=False # optional parameter, when it's True bot prints info about the called methods, False by default
        )
        if not self.async_:
            self.bot.messaging.on_message(self.on_msg, self.on_click)
        else:
            self.bot.messaging.on_message_async(self.on_msg, self.on_click)
            self.strategy()
        
    def strategy(self, *args, **kwargs):
        pass
    
    def on_msg(self, *params):
        pass
    
    def on_click(self, *params):
        pass
    
    def buttons(self, peer, title, options, uid=None):
        return self.bot.messaging.send_message(
            peer, title,
            [InteractiveMediaGroup(
                [InteractiveMedia(
                    option[0],
                    InteractiveMediaButton(
                        *option)
                        )
                for option in options]
            )], uid=uid
        ).wait()
    
    def select(self, peer, text, select_title, options, select_id="default"):
        return self.bot.messaging.send_message(peer, 
                                               text, 
                                               [InteractiveMediaGroup([InteractiveMedia(
                            select_id,
                             InteractiveMediaSelect(options, select_title, "choose"),
                            InteractiveMediaStyle.INTERACTIVEMEDIASTYLE_DANGER,
                        )])])
