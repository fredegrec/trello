BOT_TOKEN = 'd2ae02c315b4a91016d21e7f8aee5cfc20e5e63b'
BOT_ENDPOINT = 'demo-eem.transmit.im'
DBNAME = 'botstrello'
MONGODBLINK = 'mongodb://localhost:27017/'
LOGS_FILE = 'trellobot.logs'

#trello
APP_KEY = '079a5558609ec2719aa62412b30022fc' #trello's admin api key https://trello.com/app-key
ORIGIN = 'http://209.97.150.98:5000' # server address where the bot code is running(for example, http://ip:port), you need to insert it into allowed origins of the  trello's admin's account on the page https://trello.com/app-key
HOST = '209.97.150.98' #server IP where the bot code is running
PORT = 5000 # port, where bot's server listen, you need to allow this port with ufw
URL_TEMPLATE = 'https://trello.com/1/authorize?expiration=never&name=Dialog&scope=read,write,account&key={}&return_url={}/users/{}&callback_method=fragment'

CARD_PATTERN = '{}. {} из списка {} \n {} \n \n'
BOT_ANSWERS = {
    'WRONG_COMMAND': 'Такой команды нет. Вот список доступных команд: \n /trello link [url or boardname] \n /trello + [@usernames] [name] \n /trello search [cardname]' ,
    'NO_LINK_FOUND': 'Эта группа еще не связана ни с одной доской',
    'assign' : 'Теперь используйте команду /trello assign [teammates]',
    'comment': 'Теперь используйте команду /trello comment [text]',
    'SEARCH_NOT_FOUND': 'Карточки не найдены',
    'IS_OK_RES': 'Это то, что вы искали? \n {} из списка {} \n {}',
    'LIST_ADD_OK' : 'Теперь новые карточки будут добавляться в список {}',
    'USER_NOT_FOUND' : 'Пользователи {} не найдены или не авторизованы. Остальные будут назначены',
    'LINK FOUND': 'Эта группа теперь связана с доской {} \n {} \n Новые карточки сейчас добавляются в список {}',
    'NEW_LIST': 'Выберите другой список для карточек', 
    'ACTION_OK' : 'Готово', 
    'SHOW_CARD': 'Показать в чате', 
    'WHAT_CARD_SHOW': 'Какую карточку показать?',
    'NOT_AUTH': 'Вы не авторизованы. Авторизуйтесь по ссылке: {}',
    'WRONG_BOARD': 'Такой доски нет',
    'CARD' : '{} \n {} \n Чтобы оставить комментарий или назначить человека, сделайте reply на это сообщение вида "-c comment" или "-a @assignee" соответственно'
              }
CARD_OPTIONS = {'comment': 'Комментировать', 'assign': 'Назначить'}
AVAILABLE_COMMANDS = ['link', '+', 'search']
