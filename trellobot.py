from enum import Enum
import logging
import threading
import requests

from dialog_api import media_and_files_pb2, search_pb2
from dialog_bot_sdk.entities.Peer import Peer, PeerType
from dialog_bot_sdk.entities.UUID import UUID
from trello import TrelloClient
import flask
from waitress import serve

from bot import *
from config import *
from flask_app import *


class TrelloStrategy(Strategy):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kill = False         
        
    def _list_to_text(self, params, sep=' '):
        if type(params) == type([]):
            if len(params) > 1:
                return sep.join(params)
            else:
                return params[0]
    
    def _handle_command(self, peer, uid, command, params):
        token = self.db_handler.get(uid, Tables.tokens.value)
        if not token:
            self.bot.messaging.send_message(peer,
                ANSWERS['NOT_AUTH'].format(self._get_auth_link(uid)), uid=uid)
            return None
        client = TrelloClient(api_key=APP_KEY,
                              token=token
        )
        if params and type(params) == type([]) and command not in ['edit_save', 'comment_save', 'board_save', 
                                                                   'status_edit', 'show_next']:
            params = self._list_to_text(params)
        args = [peer, client]
        if peer.id != uid:
            args.append(uid)
        if params:
            args.append(params)
        getattr(self, '_handle_' + command)(*args)
    
    def _get_auth_link(self, uid):
        return URL_TEMPLATE.format(APP_KEY, ORIGIN, uid)
    
    def on_msg(self, params):
        try:
            uid = params.sender_peer.id
            group_id = params.peer.id
            peer = params.peer
            if uid != group_id:
                return
            text = params.message.text_message.text
            msg = text.split(' ')
            state = self.db_handler.get(uid, Tables.states.value)
            if not state:
                state = ''
            if text == '/start':
                self._handle_menu(peer=peer, start=True)
            if msg[0] == '/trello':
                if len(msg) == 1:
                    self._handle_menu(peer=peer, start=True)
                elif msg[1] == '+' or msg[1] == 'add':
                    self._handle_command(peer, uid, 'add', msg[2:])
                elif msg[1] in ['-c', '-с']:
                    mid = self.db_handler.get(uid, Tables.last_card.value)
                    if mid:
                        self._handle_command(peer, uid, 'comment', mid)
            elif state == States.add_save.value:
                self._handle_command(peer, uid, state, text)
            elif States.edit_save.value in state:
                val = States.edit_save.value
                self._handle_command(peer, uid, val, [state.replace(val, ''), text])
            elif States.comment_save.value in state:
                val = States.comment_save.value
                self._handle_command(peer, uid, val, [state.replace(val, ''), text])
            elif state == States.search_results.value:
                self._handle_command(peer, uid, state, text)
        except Exception as e:
            raise e
    
    def on_click(self, params):
        try:
            peer = params.peer
            value = params.value
            uid = peer.id
            param_id = params.id
            msg = value.split(SEP)
            if value == 'menu':
                self._handle_menu(peer)
            else:
                self._handle_command(peer, uid, msg[0], msg[1:])
        except Exception as e:
            raise e
            
    def _handle_menu(self, peer, start=False):
        token = self.db_handler.get(peer.id, Tables.tokens.value)
        if start:
            self.bot.messaging.send_message(peer, ANSWERS['help'].format(self.bot.users.get_user_by_id(peer.id).wait().data.name))
        if not token:
            buttons = BUTTONS['menu']
        else:
            buttons = BUTTONS['menu_auth']
        self.buttons(peer, ANSWERS['menu'], buttons)        
        
    def _handle_change_account(self, peer, client):
        for table in Tables:
            self.db_handler.delete(peer.id, table.value)
        self.bot.messaging.send_message(peer,
                ANSWERS['NOT_AUTH'].format(self._get_auth_link(peer.id)))
        
    def _get_boards(self, peer, client):
        boards = [x for x in client.get_member('me').get_boards('') if 'organization' not in dir(x)]
        if not boards:
            self.buttons(peer=peer,
                         title=ANSWERS['no_boards'], 
                         options=BUTTONS['no_boards'])
        return boards
    
    def _handle_boards(self, peer, client):
        boards = self._get_boards(peer, client)
        for board in boards:
            self.buttons(peer=peer, 
                         title=board.name, 
                         options=[('{}__{}'.format(x, board.id), y) if x != 'menu' else (x, y) for (x, y) in BUTTONS['board']])
    
    def _handle_board_select(self, peer, client, text=ANSWERS['board_select']):
        boards = self._get_boards(peer, client)
        if boards:
            self.select(peer=peer,
                       text=text,
                       select_title=None,
                       options={'board_save__{}__{}'.format(board.id, int(text==ANSWERS['board_select'])): board.name for board in boards})
    
    def _handle_board_save(self, peer, client, params):
        board = client.get_board(params[0])
        self.db_handler.save(peer.id, board.id, Tables.boards.value)
        print(params)
        if len(params) > 1:
            params[1] = int(params[1])
            if not params[1]:
                self._handle_list_select(peer, board)
                return
            elif params[1] == 2:
                self._handle_tasks(peer, client, board.id)
                return
            elif params[1] == 3:
                self._handle_search_by_name(peer, client)
                return
        self.buttons(peer=peer,
                        title=ANSWERS['board_save'].format(board.name, board.url),
                        options=[('{}__{}'.format(x, board.id), y) if x in BOARD_COMMANDS else (x, y) for (x, y) in BUTTONS['board_save']])
        
    def _handle_add(self, peer, client, text=None):
        board_id = self.db_handler.get(peer.id, Tables.boards.value)
        if text:
            self.db_handler.save(peer.id, text, Tables.add_text.value)
        if not board_id:
            self._handle_board_select(peer, client, ANSWERS['add_no_boards'])
        else:
            self._handle_list_select(peer, client.get_board(board_id))
            
    def _get_lists(self, peer, board):
        lists = board.all_lists()
        if not lists:
            self.buttons(peer=peer,
                        title=ANSWERS['no_lists'].format(board.name, board.url),
                        options=BUTTONS['no_lists'])
        return lists
    
    def _handle_list_select(self, peer, board):
        lists = self._get_lists(peer, board)
        if lists:
            self.select(peer=peer,
                        text=ANSWERS['add_list_select'],
                        select_title=None,
                        options={'list_save__{}'.format(l.id): l.name for l in lists})
                        
    def _handle_list_save(self, peer, client, list_id):
        self.db_handler.save(peer.id, list_id, Tables.lists.value)
        self.db_handler.save(peer.id, States.add_save.value, Tables.states.value)
        text = self.db_handler.get(peer.id, Tables.add_text.value)
        if not text:
            self.bot.messaging.send_message(peer, ANSWERS['add'])
        else:
            self._handle_add_save(peer, client, text)
            self.db_handler.db.add_text.delete_one({'_id': peer.id})
        
    def _card_options(self, card_id):
        return [('{}__{}'.format(x, card_id), y) if x in CARD_COMMANDS else (x, y) for (x, y) in BUTTONS['card']]
        
    def _handle_add_save(self, peer, client, text):
        self.db_handler.reset_state(peer.id)
        card = client.get_list(self.db_handler.get(peer.id, Tables.lists.value)).add_card(name=text)
        self.db_handler.save(peer.id, card.id, Tables.last_card.value)
        self.buttons(peer=peer,
                    title=ANSWERS['add_success'].format(card.url),
                    options=self._card_options(card.id))
        
    def _handle_delete(self, peer, client, card_id):
        card = client.get_card(card_id)
        self.buttons(peer=peer,
                     title=ANSWERS['delete'].format(card.name, client.get_board(card.board_id).name),
                     options=[('{}__{}'.format(x, card_id), y) for (x, y) in BUTTONS['delete']])
        
    def _handle_delete_confirmed(self, peer, client, card_id):
        card = client.get_card(card_id)
        name = card.name
        card.delete()
        self.buttons(peer=peer,
                    title=ANSWERS['delete_confirmed'].format(name),
                    options=[(x, y) for (x, y) in BUTTONS['card'] if x not in CARD_COMMANDS])
        
    def _handle_delete_cancel(self, peer, client, card_id):
        card = client.get_card(card_id)
        self.buttons(peer=peer,
                    title=ANSWERS['delete_cancel'].format(card.name, card.url),
                    options=self._card_options(card.id))
        
    def _handle_status(self, peer, client, card_id):
        card = client.get_card(card_id)
        lists = self._get_lists(peer, client.get_board(card.board_id))
        if lists:
            self.select(peer=peer,
                        text=ANSWERS['status'],
                        select_title=None,
                        options={'status_edit__{}__{}'.format(card.id, l.id): l.name for l in lists})
            
    def _handle_status_edit(self, peer, client, params):
        card = client.get_card(params[0])
        card.change_list(params[1])
        self.buttons(peer=peer,
                    title=ANSWERS['status_edit'].format(card.name, client.get_list(params[1]).name, card.url),
                    options=self._card_options(card.id))
        
    def _handle_edit(self, peer, client, card_id):
        self.db_handler.save(peer.id, States.edit_save.value + card_id, Tables.states.value)
        self.bot.messaging.send_message(peer, ANSWERS['edit'])
        
    def _handle_edit_save(self, peer, client, params):
        [card_id, text] = params
        self.db_handler.reset_state(peer.id)
        card = client.get_card(card_id)
        card.set_name(text)
        self.buttons(peer=peer,
                     title=ANSWERS['edit_save'].format(text, card.url),
                     options=self._card_options(card.id)
        )
        
    def _handle_comment(self, peer, client, card_id):
        self.db_handler.save(peer.id, States.comment_save.value + card_id, Tables.states.value)
        self.bot.messaging.send_message(peer, ANSWERS["comment"])
        
    def _handle_comment_save(self, peer, client, params):
        self.db_handler.reset_state(peer.id)
        card = client.get_card(params[0])
        card.comment(params[1])
        self.buttons(peer=peer,
                     title=ANSWERS['comment_save'].format(card.url),
                     options=self._card_options(card.id))
        
    def _print_cards(self, peer, cards, boards, params):
        num = len(cards)
        if num > 10 and not params:
            if len(boards) == 1:
                title = ANSWERS['tasks']
                board_id = boards[0].id
            else:
                title = ANSWERS['search_res']
                board_id = None
            self.buttons(peer=peer,
                         title=title.format(num),
                         options=self._board_options(name='tasks',
                                            board_id=board_id))
            return
        elif num == 0:
            self.buttons(peer=peer,
                         title=ANSWERS['no_res'],
                         options=BUTTONS['no_res'])
        if params and params['page'] >= 0:
            (cards, last) = self._filter_cards(peer, cards, **params)
        lists = []
        for board in boards:
            lists += board.all_lists()
        for card in cards:
            self.buttons(peer=peer,
                         title=ANSWERS['card_info'].format(card.name, 
                                                           [l.name for l in boards if l.id == card.board_id][0], 
                                                           card.card_created_date, 
                                                           [l.name for l in lists if l.id == card.list_id][0],
                                                           card.url),
                         options=[('{}__{}'.format(x, card.id), y) if x in CARD_COMMANDS else (x, y) for (x, y) in BUTTONS['card_info']])
        if params and params['page'] >= 0 and not last:
            self.buttons(peer=peer,
                         title=' ',
                         options=[('show_next__{}__{}__{}'.format(boards[0].id if len(boards) == 1 else 0, 
                                                                  params['page']+1, params['how']
                                                         ), 'Показать еще')])   
            
    def _handle_show_next(self, peer, client, params):
        board_id = params[0]
        params = [int(x) for x in params[1:]]
        if board_id == "0":
            self._handle_search_results(peer, client, params={'page':params[0], 'how': params[1]})
        else:
            self._handle_tasks(peer, client, board_id, params={'page':params[0], 'how': params[1]})
    
    def _board_options(self, name, board_id=None):
        return [('{}__{}'.format(x, board_id), y) if board_id else (x, y) for (x, y) in BUTTONS[name]]
        
    def _handle_tasks(self, peer, client, board_id=None, params=None):
        if not board_id:
            board_id = self.db_handler.get(peer.id, Tables.boards.value)
            if not board_id:
                self.select(peer=peer,
                            text=ANSWERS['search_board_select'],
                            select_title=None,
                            options={'board_save__{}__2'.format(board.id): board.name for board in self._get_boards(peer, client)})
                return
        board = client.get_board(board_id)
        self._print_cards(peer, board.all_cards(), [board], params)
        
    def _get_params(self, page=0, how=0):
        return {'page': page, 'how': how}
            
    def _handle_show_all(self, peer, client, board_id=None):
        if board_id:
            self._handle_tasks(peer, client, board_id, params={'page':-1, 'how': 0})
        else:
            self._handle_search_results(peer, client, params={'page':-1, 'how': 0})
        
    def _handle_show_ten(self, peer, client, board_id=None):
        self.buttons(peer=peer,
                    title=ANSWERS['show_ten'],
                    options=[('{}__{}'.format(x, board_id), y) if board_id else (x, y) for (x, y) in BUTTONS['show_ten']])
        
    def _filter_cards(self, peer, cards, how, page=0):
        date = self.db_handler.get(peer.id, Tables.card_dates.value)
        if how == Sorted.by_name.value:
            cards = sorted(cards, key=lambda x: x.name.lower())
        else:
            cards = sorted(cards, key=lambda x: x.card_created_date, reverse=how)
        if date:
            cards = [x for x in cards if x.card_created_date <= date]
        else:
            self.db_handler.save(peer.id, max(cards, key=lambda x: x.card_created_date).card_created_date, Tables.card_dates.value)
        last = len(cards) <= (page+1)*10
        cards = cards[page*10: (page+1)*10]
        return (cards, last)
        
    def _handle_old(self, peer, client, board_id=None):
        if board_id:
            self._handle_tasks(peer, client, board_id, {'page':0, 'how': 0})
        else:
            self._handle_search_results(peer, client, params={'page':0, 'how': 0})
        
    def _handle_new(self, peer, client, board_id=None):
        if board_id:
            self._handle_tasks(peer, client, board_id, {'page':0, 'how': 1})
        else:
            self._handle_search_results(peer, client, params={'page':0, 'how': 1})
            
    def _handle_alphabet(self, peer, client, board_id=None):
        if board_id:
            self._handle_tasks(peer, client, board_id, {'page':0, 'how': 2})
        else:
            self._handle_search_results(peer, client, params={'page':0, 'how': 2})
        
    def _handle_search(self, peer, client):
        self.buttons(peer=peer,
                     title=ANSWERS['search'],
                     options=BUTTONS['search'])
        
    def _handle_search_by_board(self, peer, client):
        boards = self._get_boards(peer, client)
        if boards:
            self.select(peer=peer,
                       text=ANSWERS['board_select'],
                       select_title=None,
                       options={'tasks__{}'.format(board.id): board.name for board in boards})
    
    def _handle_search_by_name(self, peer, client):
        board_id = self.db_handler.get(peer.id, Tables.boards.value)
        if not board_id:
            self.select(peer=peer,
                            text=ANSWERS['search_board_select'],
                            select_title=None,
                            options={'board_save__{}__3'.format(board.id): board.name for board in self._get_boards(peer, client)})
            return
        self.db_handler.save(peer.id, States.search_results.value, Tables.states.value)
        self.bot.messaging.send_message(peer, ANSWERS['search_by_name'])
        
    def _handle_search_results(self, peer, client, text=None, params=None):
        if text:
            self.db_handler.reset_state(peer.id)
            self.db_handler.save(peer.id, text, Tables.query.value)
        else:
            text = self.db_handler.get(peer.id, Tables.query.value)
        board_id = self.db_handler.get(peer.id, Tables.boards.value)
        cards = client.search(text, partial_match=True, models=['cards'], cards_limit=1000, board_ids=[board_id])
        self._print_cards(peer, cards, client.list_boards(), params)
            
                               
        
        
     
            
class BotWrapper(object):
    def __init__(self):
        self.strategy = TrelloStrategy(token=BOT_TOKEN,
                                           endpoint=BOT_ENDPOINT,async_=False,
                                      db_link=MONGODBLINK, db_name=DBNAME) 
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
    thread.daemon = True
    thread.start()
    #app.run(host=IP)
    #serve(app, port=PORT, host=HOST)#, port=PORT)
    create_app(wrapper)
