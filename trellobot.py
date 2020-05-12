from enum import Enum
import logging
from dialog_api import media_and_files_pb2, search_pb2
from dialog_bot_sdk.entities.Peer import Peer, PeerType
from dialog_bot_sdk.entities.UUID import UUID
from pymongo import MongoClient
import requests
from trello import TrelloClient
import flask
import threading
from waitress import serve
from bot import *
from config import *
from flask_app import app
    
class Tables(Enum):
    tokens = 'tokens'
    teams = 'teams'
    lists = 'lists'
    states = 'actions'


class RemindStrategy(Strategy):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = MongoClient(MONGODBLINK)
        self.db = self.client[DBNAME]
        self.kill = False
        
    def get_value(self, uid, table):
        val = self.db[table].find_one({'_id': uid})
        if val is None:
            return None
        return val['value']
    
    def get(self, _id, table):
        return self.db[table].find_one({'_id': _id})
        
    def reset_state(self, uid):
        return self.set_value(uid, States.START.value, Tables.STATES.value)
    
    def increment_value(self, uid, value, table):
        self.set_value(uid, str(int(value) + 1), table)
                
    def set_value(self, uid, value, table):
        self.db[table].replace_one({'_id': uid}, {'value': value}, upsert=True)
        return value 
    
    def update_value(self, _id, field, value, table):
        self.db[table].update_one({"_id": _id}, {"$set": {field: value}})         
    
    def _handle_link(self, peer, uid, client, link):  
        try:
            if 'trello.com' in link:
                board = [board for board in client.list_boards() if board.url == link][0]
            else:
                board = [board for board in client.list_boards() if board.name == link][0]
        except:
            self.bot.messaging.send_message(peer, BOT_ANSWERS['WRONG_BOARD'])
            return
        lists = [(x.id, x.name) for x in board.all_lists()]
        if len(lists) == 0:
            self.db.links.replace_one({'_id': peer.id}, {'board': board.id, 'list': None}, upsert=True)
            self.bot.messaging.send_message(peer, 'Эта группа теперь связана с доской {} \n {} \n . На доске нет списков. Карточки не смогут добавляться'.format(
                board.name, board.url))
        else:
            self.db.links.replace_one({'_id': peer.id}, {'board': board.id, 'list': lists[0][0]}, upsert=True)        
            self.bot.messaging.send_message(peer, 
                 BOT_ANSWERS['LINK FOUND'].format(board.name, board.url, lists[0][1]), self.select(BOT_ANSWERS['NEW_LIST'], {'list_{}_{}_{}'.format(_id, peer.id, name): str(name) 
                                                                       for (_id, name) in lists}, 'list'))   
        
    def _list_to_text(self, params, sep=' '):
        if type(params) == type([]):
            if len(params) > 1:
                return sep.join(params)
            else:
                return params[0]
    
    def _handle_add(self, peer, uid, client, params):
        link = self.get(peer.id, 'links')
        if not link:
            self.bot.messaging.send_message(peer, BOT_ANSWERS['NO_LINK_FOUND'], uid=uid)
            return      
        if not link['list']:
            self.bot.messaging.send_message(peer, 'Список для карточек не выбран', uid=uid)
            return
        name = self._list_to_text([param for param in params if not param.startswith('@')])
        nicks = [param for param in params if param.startswith('@')]
        members = self._get_members_by_nick(peer, uid, nicks)
        board_list = client.get_list(link['list'])
        card = board_list.add_card(name=name, assign=members)
        self.bot.messaging.send_message(peer, BOT_ANSWERS['CARD'].format(name, card.url)) 
        
    def _get_members_by_nick(self, peer, uid, nicks):
        if nicks:
            nicks = [param.replace('@', '') for param in nicks if param.startswith('@')]
            members = {self._get_id_by_nick(member): member for member in nicks}
            tokens = self.db["tokens"].find({"_id" : {"$in" : list(members.keys())}})
            tokens = [x for x in tokens]
            not_found = ["@" + member for (_id, member) in members.items() if _id not in [x['_id'] for x in tokens]]
            if not_found:
                self.bot.messaging.send_message(peer, 
                            BOT_ANSWERS['USER_NOT_FOUND'].format(self._list_to_text(not_found, ", ")), uid=uid)
            members = [TrelloClient(api_key=APP_KEY, token=token["value"]).get_member('me') for token in tokens]
            return members
        return []

    def _card_by_url(self, peer, uid, client, url):
        board = self.get(peer.id, 'links')['board']
        board = client.get_board(board)
        return [card for card in board.all_cards() if card.url == url][0]

    def _handle_assign(self, peer, uid, client, nicks):
        members = self._get_members_by_nick(peer, uid, nicks[:-1])
        card = self._card_by_url(peer, uid, client, nicks[-1])
        for member in members:
            card.assign(member.id)
        self.bot.messaging.send_message(peer, BOT_ANSWERS['ACTION_OK'], uid=uid)
        

    def _handle_comment(self, peer, uid, client, comment):
        card = self._card_by_url(peer, uid, client, comment[-1])
        card.comment(comment[0])
        self.bot.messaging.send_message(peer, BOT_ANSWERS['ACTION_OK'], uid=uid)
    
    def _handle_search(self, peer, uid, client, query):
        link = self.get(peer.id, 'links')
        if not link:
            self.bot.messaging.send_message(peer, BOT_ANSWERS['NO_LINK_FOUND'], uid=uid)
            return
        cards = client.search(query, models=['cards'], board_ids=[link['board'],])
        if len(cards) == 0:
            self.bot.messaging.send_message(peer, BOT_ANSWERS['SEARCH_NOT_FOUND'], uid=uid)
        elif len(cards) == 1:
            card = cards[0]
            list_ = client.get_list(card.idList)
            self.buttons(peer, BOT_ANSWERS['IS_OK_RES'].format(card.name, list_.name, card.url), [('card_{}_{}_{}'.format(card.id, card.name, peer.id), BOT_ANSWERS['SHOW_CARD'])], uid=uid)
        else:
            descr = []
            options = {}
            for (i, card) in enumerate(cards):
                list_ = client.get_list(card.idList)
                descr.append(CARD_PATTERN.format(i+1, card.name, list_.name, card.url))
                options["card_{}_{}_{}".format(card.id, card.name, peer.id)] =  str(i+1)
            descr = self._list_to_text(descr)
            self.bot.messaging.send_message(peer, descr, self.select(BOT_ANSWERS['WHAT_CARD_SHOW'], options, 'search'), uid=uid)
    
    def _handle_command(self, peer, uid, command, params):
        token = self.get_value(uid, 'tokens')
        if not token:
            self.bot.messaging.send_message(peer,
                BOT_ANSWERS['NOT_AUTH'].format(self._get_auth_link(uid)), uid=uid)
            return None
        client = TrelloClient(
            api_key=APP_KEY,
            token=token
        )
        if type(params) == type([]) and command not in ['add', 'assign']:
            if command == 'comment':
                url = params[-1]
                params = params[:-1]
            if len(params) > 1:
                params = ' '.join(params)
            else:
                params = params[0]
            if command == 'comment':
                params = [params, url]
        getattr(self, '_handle_' + command)(peer, uid, client, params)
    
    def _get_auth_link(self, uid):
        return URL_TEMPLATE.format(APP_KEY, ORIGIN, uid)
    
    def _get_id_by_nick(self, nick):
        request = search_pb2.RequestResolvePeer(
                shortname=nick
            )
        result = self.bot.internal.search.ResolvePeer(request)
        if hasattr(result, "peer"):
            self.bot.manager.add_out_peer(result.peer)
            return result.peer.id
    
    def on_msg(self, params):
        try:
            uid = params.sender_peer.id
            group_id = params.peer.id
            peer = params.peer
            if uid == group_id:
                return
            msg = params.message.text_message.text.split(' ')
            if msg[0] in ['-c', '-a', '-с', '-а']:
                reply_text = self.bot.messaging.get_messages_by_id(params.reply).wait()[0].message.text_message.text.split(' ')
                url = [x for x in reply_text if 'trello.com' in x]
                if url:
                    url = url[0]
                    params = msg[1:]
                    params.append(url)
                    if msg[0] in ['-c', '-с']:
                        self._handle_command(peer, uid, 'comment', params)
                    else:
                        self._handle_command(peer, uid, 'assign', params)
            if msg[0] == '/trello':
                if len(msg) > 2 and msg[1] in AVAILABLE_COMMANDS:
                    if msg[1] == '+':
                        msg[1] = 'add'
                    self._handle_command(peer, uid, msg[1], msg[2:])    
                else:
                    self.bot.messaging.send_message(peer, BOT_ANSWERS['WRONG_COMMAND'], uid=uid)
        except Exception as e:
            raise e
    
    def on_click(self, params):
        try:
            peer = params.peer
            value = params.value
            uid = peer.id
            param_id = params.id
            if param_id == 'list':
                (_, list_id, group, name) = value.split('_')
                group = int(group)
                self.update_value(group, 'list', list_id, 'links')
                self.bot.messaging.send_message(Peer(group, PeerType.PEERTYPE_GROUP),
                                                BOT_ANSWERS['LIST_ADD_OK'].format(name))
            elif 'assign_' in value or 'comment_' in value:
                (action, card, group) = value.split('_')
                self.set_value(uid, card, 'action')
                self.bot.messaging.send_message(Peer(int(group), PeerType.PEERTYPE_GROUP), BOT_ANSWERS[action], uid=uid)
            elif 'card_' in value:
                (_, card_id, name, group) = value.split('_')
                token = self.get_value(uid, 'tokens')
                card = TrelloClient(api_key=APP_KEY, token=token).get_card(card_id)
                peer = Peer(int(group), PeerType.PEERTYPE_GROUP)
                self.bot.messaging.send_message(peer, BOT_ANSWERS['CARD'].format(name, card.url))
        except Exception as e:
            raise e
            
class BotWrapper(object):
    def __init__(self):
        self.strategy = RemindStrategy(token=BOT_TOKEN,
                                           endpoint=BOT_ENDPOINT,async_=False) 
        self.logger = logging.getLogger('remindbot')
        self.logger.setLevel(logging.DEBUG)
        ch = logging.FileHandler(LOGS_FILE)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
    def run(self):
        while True:
            try:
                self.logger.info('Start')
                self.strategy.start()
            except Exception as e:
                self.logger.exception(e)

                
if __name__=='__main__':
    wrapper = BotWrapper()
    thread = threading.Thread(target=wrapper.run, args=())
    thread.start()
    #app.run(host=IP)
    serve(app, host=HOST, port=PORT)
