BOT_TOKEN = ''
BOT_ENDPOINT = 'demo-eem.transmit.im'
DBNAME = 'trellobot'
MONGODBLINK = 'mongodb://localhost:27017/'
LOGS_FILE = 'trellobot.logs'

#trello
APP_KEY = '079a5558609ec2719aa62412b30022fc' #trello's admin api key https://trello.com/app-key
ORIGIN = 'http://64.227.11.35:5000' # server address where the bot code is running(for example, http://ip:port), you need to insert it into allowed origins of the  trello's admin's account on the page https://trello.com/app-key
HOST = '64.227.11.35' #server IP where the bot code is running
PORT = 5000 # port, where bot's server listen, you need to allow this port with ufw
URL_TEMPLATE = 'https://trello.com/1/authorize?expiration=never&name=Dialog&scope=read,write,account&key={}&return_url={}/users/{}&callback_method=fragment'

SEP = '__'
ANSWERS = {
    'NOT_AUTH': 'Вы не авторизованы. Авторизуйтесь по ссылке: {}',
    'menu' : '[Как я могу вам помочь?](https://trello.com/user/boards)',
    'no_boards': '[У вас нет ни одной доступной доски. Перейдите в Trello](https://trello.com/user/boards)',
    'no_lists': '[На доске {} нет списков]({})',
    'board_select': 'Выберите доску',
    'board_save': '[Активная доска {}. Изменить доску можно в пункте "Выбор доски". Что делаем на доске?]({})',
    'add_no_boards': 'Ни одна доска еще не была выбрана. Выберите доску, на которой хотите создать задачу',
    'add_list_select': 'Выберите колонку доски для создания задачи',
    'add': 'Пришлите задачу в ответ на это сообщение', 
    'add_success': '[Задача создана! Что делаем?]({})',
    'delete': 'Удалить задачу {} с доски {}? Восстановление будет невозможно',
    'delete_confirmed': '[Задача {} удалена. Что делаем?](https://trello.com/user/boards)',
    'delete_cancel': '[Удаление задачи {} отменено. Что делаем?]({})',
    'status': 'Выберите новый статус для задачи', 
    'status_edit': '[Задача {} перенесена в колонку {}. Что делаем?]({})',
    'edit': 'Пришлите новое название задачи в ответ на сообщение',
    'edit_save': '[Задача изменена! Новое название: {}. Что делаем?]({})',
    'comment': 'В ответ на это сообщение отправьте текст комментария',
    'comment_save': '[Комментарий добавлен. Что делаем?]({})',
    'tasks': 'На доске {} задач. Как их отобразить?',
    'card_info': '[название задачи: {} \n название доски: {} \n дата создания: {} \n статус: {}]({})',
    'show_ten': 'Выберите способ сортировки',
    'search': 'Выберите опцию поиска',
    'search_by_board': 'Укажите доску для поиска',
    'search_by_name': 'Укажите название задачи для поиска',
    'no_res': 'Найдено 0 результатов. Продолжить поиск?',
    'search_res': 'Найдено {} результатов. Как их отобразить?',
    'search_board_select': 'Ни одна доска еще не была выбрана. Выберите доску'
              }
BUTTONS = {
    'card': [('board_select', 'Выбор доски'), ('add', 'Новая задача'), ('edit', 'Редактировать'), ('status', 'Изменить статус'), ('delete', 'Удалить'), ('tasks', 'Все задачи'), ('search', 'Поиск'), ('comment', 'Добавить комментарий'), ('menu', 'В меню')],
    'menu': [('boards', 'Все доски'), ('board_select', 'Выбор доски'), ('add', 'Новая задача'), ('tasks', 'Все задачи'), ('search','Поиск')],
    'menu_auth': [('change_account', 'Сменить аккаунт Trello'), ('boards', 'Все доски'), ('board_select', 'Выбор доски'), ('add', 'Новая задача'), ('tasks', 'Все задачи'), ('search','Поиск')],
    'no_boards': [('menu', 'Вернуться в меню')],
    'no_lists': [('menu', 'Вернуться в меню')],
    'board': [('board_save', 'Выбрать доску'), ('menu', 'Вернуться в меню')],
    'board_save': [('add', 'Новая задача'), ('tasks', 'Все задачи'), ('search', 'Поиск'), ('menu', 'В меню')],
    'delete': [('delete_confirmed', 'Удалить'), ('delete_cancel', 'Отменить')],
    'tasks': [('show_ten', 'Показывать по 10'), ('show_all', 'Показать все')],
    'card_info': [('edit', 'Редактировать'), ('status', 'Изменить статус'), ('delete', 'Удалить'), ('comment', 'Добавить комментарий'), ('menu', 'В меню')],
    'show_ten': [('old', 'Сначала старые'), ('new', 'Сначала новые'), ('alphabet', 'По алфавиту')],
    'search': [('search_by_board', 'По доске'), ('search_by_name', 'По названию')],
    'no_res': [('search', 'Продолжить'), ('menu', 'В меню')]
    
}
CARD_COMMANDS = ['comment', 'edit', 'delete', 'status']
BOARD_COMMANDS = ['tasks',  'trello']

