from flask import Flask, request, redirect, render_template
from pymongo import MongoClient
from waitress import serve
from dialog_bot_sdk.entities.Peer import Peer, PeerType

from config import *

def create_app(wrapper):
    app = Flask(__name__)

    @app.route('/success', methods=['GET'])
    def success():
        return ''

    @app.route('/users/<uid>', methods=["GET", "POST"])
    def save_token(uid):
        if request.method == "POST":
            db = MongoClient(MONGODBLINK)[DBNAME]
            db["tokens"].replace_one({'_id': int(uid)}, {'value': request.form["token"].replace('#token=', '')}, upsert=True)
            peer = Peer(int(uid), PeerType.PEERTYPE_PRIVATE)
            wrapper.strategy.bot.messaging.send_message(peer, 
                    ANSWERS['auth_success'].format(wrapper.strategy.bot.users.get_user_by_id(int(uid)).wait().data.name))
            wrapper.strategy._handle_menu(peer)
            return redirect('/success')
        else:
            return render_template('main.html')
        
    serve(app, port=PORT, host=HOST)

if __name__=='__main__':
    app.config.update(SESSION_COOKIE_NAME='new_c')
    app.run(port='2222')
