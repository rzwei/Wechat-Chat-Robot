import logging
import multiprocessing
import os
import time

import pymysql
from flask import Flask, render_template, redirect, url_for, Response, request, session

import config
import weixin
from weixin import weixin

processes = []

app = Flask(__name__)
app.config['instances'] = []


def myprint(*args):
    m = ''
    for x in args:
        m += ' ' + str(x)
    print(m)
    try:
        logging.info(m)
    except Exception as e:
        print(e)


class MyDb:
    def __enter__(self):
        self.db = pymysql.connect(
            host=config.dbaddress, user=config.dbusername, password=config.dbpassword)

        self.cx = self.db.cursor()
        self.db.autocommit(1)

        self.db.set_charset("utf8mb4")
        self.cx.execute('SET NAMES utf8mb4;')
        self.db.commit()
        self.cx.execute(
            "create database if not exists db_weixin DEFAULT CHARACTER SET utf8mb4")
        self.db.commit()

        self.cx.execute("use db_weixin;")
        self.db.commit()
        return self.cx

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.db.commit()
            self.cx.close()
            self.db.close()
        except Exception as e:
            myprint('db error', e)


class dbHelper:
    pass


@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('login'):
        return redirect(url_for('login'))
    for pic in config.picname:
        path = os.path.join(config.imagepath, pic)

        request.files['picture'].seek(0)

        picture = request.files['picture'].read()

        with open(path, 'wb') as fout:
            fout.write(picture)

    return '上传成功'


@app.route('/menu')
def menu():
    if not session.get('login'):
        return redirect(url_for('login'))

    instances = []
    for p in app.config['instances']:
        if p.is_alive():
            instances.append(p)
        else:
            p.terminate()

    app.config['instances'] = instances
    return render_template('menu.html', instances=instances)


@app.route('/new')
def new():
    if not session.get('login'):
        return redirect(url_for('login'))

    return render_template('new.html')


@app.route('/')
def index():
    return redirect(url_for('login'))


def start_instance(path):
    weixin.run(path)


@app.route('/start')
def start():
    if not session.get('login'):
        return redirect(url_for('login'))

    alive = 0
    
    for i in app.config['instances']:
        if i.is_alive():
             alive += 1
    
    if alive >= config.aliveCount:
        return redirect(url_for('menu'))

    qrpath = session['qrpath']

    if os.path.exists(qrpath):
        os.remove(qrpath)

    p = multiprocessing.Process(target=start_instance, args=(qrpath,))
    app.config['instances'].append(p)
    p.start()
    return redirect(url_for('qr'))


@app.route('/test')
def test():
    return render_template('test.html')


@app.route('/qr')
def qr():
    if not session.get('login'):
        return redirect(url_for('login'))
    qrpath = session['qrpath']
    tryTimes = 15
    while tryTimes > 0:
        tryTimes -= 1
        if os.path.exists(qrpath):
            image = open(qrpath, 'rb')
            res = Response(image, mimetype='image/jpeg')
            return res
        time.sleep(1)
    return 'fail'


@app.route('/login', methods=['POST', 'GET'])
def login():
    if session.get('login'):
        return redirect(url_for('new'))

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        if request.form['account'] != config.account or request.form['password'] != config.password:
            return redirect(url_for('login'))
        session['login'] = True
        session['qrpath'] = os.path.join(
            config.basepath, str(int(time.time())))
    return redirect(url_for('new'))


if __name__ == '__main__':
    # basePath = os.getcwd()
    # print(basePath)
    os.chdir(config.basepath)

    app.config['SECRET_KEY'] = os.urandom(24)

    app.run(host=config.host, port=int(config.port), debug=False, threaded=True)
