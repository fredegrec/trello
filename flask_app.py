from flask import Flask, request, redirect, render_template
from pymongo import MongoClient
from config import *
app = Flask(__name__)

@app.route('/success', methods=['GET'])
def success():
    return ''

@app.route('/users/<uid>', methods=["GET", "POST"])
def save_token(uid):
    if request.method == "POST":
        db = MongoClient(MONGODBLINK)[DBNAME]
        db["tokens"].replace_one({'_id': int(uid)}, {'value': request.form["token"].replace('#token=', '')}, upsert=True)
        return redirect('/success')
    else:
        return render_template('main.html')

if __name__=='__main__':
    app.config.update(SESSION_COOKIE_NAME='new_c')
    app.run(port='2222')
