from flask import Flask, render_template, request
from fdb_tool.fdb_test import *

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'GET':
        return render_template('query.html')
    if request.method == 'POST':
        city = request.form.get('city')
        name = request.form.get('name')
        items = get_all_concerts(db, (name, city))
        return render_template('query_result.html', items=items)


@app.route('/order', methods=['POST'])
def order():
    city = request.json['city']
    name = request.json['name']
    month = request.json['month']
    userid = request.json['userid']
    signup(db, "s" + userid, (name, city, month))
    return '', 200


@app.route('/user', methods=['GET', 'POST'])
def userq():
    if request.method == 'GET':
        return render_template('userticket.html')
    if request.method == 'POST':
        userid = request.form.get('userid')
        tickets = get_all_attends(db, ("s" + userid,))
        return render_template('userticket_result.html', tickets=tickets, userid=userid)


if __name__ == '__main__':
    app.run()
