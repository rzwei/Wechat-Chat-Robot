#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import logging
import os
import queue
import random
import re
import threading
import time

import itchat
import pymysql
import requests

import config

db = None

add_lock = threading.Lock()

robotChat = False

robotReply = False
qrpath = None
qrtimes = 5

verfiyContent = '请先发送朋友验证请求，对方验证通过后，才能聊天'

addFriendContent = '你已添加了(.*?)，现在可以开始聊天了。'

addFriendContentPattern = re.compile(addFriendContent)

addFriendsQueue = queue.Queue()

sendPictureLock = threading.Lock()

set_Alias_lock = threading.Lock()


def myprint(*args):
    m = ''
    for x in args:
        m += ' ' + str(x)
    print(m)
    try:
        logging.info(m)
    except Exception as e: 
        print(e)


def mySendPic(userName, pic_path):
    global sendPictureLock
    sendPictureLock.acquire()
    tryTimes = 3
    try:
        while tryTimes > 0:
            if itchat.send_image(pic_path, userName):
                break
            time.sleep(random.randint(3, 5))
            tryTimes -= 1
    except Exception as e:
        myprint(e)
    finally:
        sendPictureLock.release()


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


class dbHelper_mysql:
    def __init__(self, dbName):
        self.dbName = 'friends_' + dbName
        with MyDb() as cx:
            cx.execute(
                "CREATE TABLE IF NOT EXISTS " + self.dbName + "  (userid varchar(256) primary key, state INT,message TEXT,updatetime INT) character set utf8mb4")

    def insertFriend(self, friendid, state=0, message='', updatetime=None):

        if self.isFriend(friendid):
            return
        if updatetime is None:
            updatetime = int(time.time())

        with MyDb() as cx:
            try:
                cx.execute("INSERT INTO " + self.dbName + " VALUES (%s,%s,%s,%s)",
                           (friendid, state, message, updatetime))
            except:
                myprint('insert fail')
                return
        try:
            myprint('insert friend finished', friendid)
        except:
            myprint('insert friend finished')

    def isFriend(self, friendid):
        with MyDb() as cx:
            try:
                rows = cx.execute(
                    "SELECT * FROM " + self.dbName + " WHERE userid=%s", (friendid,))
            except Exception as e:
                rows = 0
                myprint(e)

        try:
            myprint('isFriend finished', friendid)
        except:
            myprint('isFriend finished')

        return True if rows != 0 else False

    def getFriendState(self, friendid):
        with MyDb() as cx:
            try:
                cx.execute(
                    "SELECT state FROM " + self.dbName + " WHERE userid=%s", (friendid,))
                for row in cx.fetchall():
                    return row[0]
            except Exception as e:
                myprint(e)
        try:
            myprint('getfriendstate finished', friendid)
        except:
            myprint('getfriendstate finished')
        return None

    def setFriendState(self, friendid, state):
        with MyDb() as cx:
            try:
                cx.execute(
                    "UPDATE " + self.dbName + " SET state=%s , updatetime=%s WHERE userid=%s",
                    (state, int(time.time()), friendid))
            except Exception as e:
                myprint(e)
        try:
            myprint('set friend state finished', friendid)
        except:
            myprint('set friend state finished')

    def addFriendState(self, friendid):
        with MyDb() as cx:
            try:
                cx.execute(
                    "UPDATE " + self.dbName + " SET state=state+1 , updatetime=%s WHERE userid=%s",
                    (int(time.time()), friendid,))
            except Exception as e:
                myprint(e)
        try:
            myprint('add friend state finished', friendid)
        except:
            myprint('add friend state finished')

    def getFriends(self, states):
        ret = []
        states = '(' + ','.join(list(map(str, states))) + ')'
        with MyDb() as cx:
            try:
                cx.execute("select userid from " + self.dbName + " where state in " + states + " and updatetime <%s",
                           (int(time.time()) - 12 * 3600,))
                for row in cx.fetchall():
                    ret.append(row[0])
            except Exception as e:
                myprint(e)
        return ret

    def getFriendTime(self, friendid):
        ret = int(time.time())
        with MyDb() as cx:
            try:
                cx.execute(
                    "SELECT updatetime FROM " + self.dbName + " WHERE userid=%s", (friendid,))
                for row in cx.fetchall():
                    ret = row[0]
            except Exception as e:
                myprint(e)
        try:
            myprint('get friend time finished!', friendid)
        except:
            myprint('get friend time finished!')
        return ret

    def setFriendTime(self, friendid, t=None):
        if t is None:
            t = int(time.time())
        with MyDb() as cx:
            try:
                cx.execute(
                    "UPDATE " + self.dbName + " SET updatetime=%s WHERE userid=%s", (t, friendid))
            except Exception as e:
                myprint(e)
        try:
            myprint('set updatetime finished', friendid)
        except:
            myprint('set updatetime finished')

    def getRandomFriend(self):
        now = int(time.time())
        with MyDb() as cx:
            try:
                cx.execute(
                    "SELECT userid FROM " + self.dbName + " WHERE updatetime<=%s AND state=0", (now - 24 * 60 * 60))
                myprint('get random friend finished')
                users = []
                for row in cx.fetchall():
                    users.append(row)
                if len(users) > 0:
                    index = random.randint(0, len(users) - 1)
                    for i, row in enumerate(users):
                        if i == index:
                            return row[0]
                else:
                    return None
            except Exception as e:
                myprint('db', e)
                return None

    def getWeekFriend(self):
        now = int(time.time())
        with MyDb() as cx:
            try:
                cx.execute(
                    "SELECT userid FROM " + self.dbName +
                    " WHERE updatetime<=%s ",
                    (now - 7 * 24 * 60 * 60,))
                myprint('get week friend finished')
                users = []
                for row in cx.fetchall():
                    users.append(row)
                if len(users) > 0:
                    index = random.randint(0, len(users) - 1)
                    for i, row in enumerate(users):
                        if i == index:
                            return row[0]
                else:
                    return None
            except Exception as e:
                myprint(e)
                return None

    def clearDB(self):
        with MyDb() as cx:
            try:
                cx.execute("DELETE FROM " + self.dbName)
            except Exception as e:
                myprint(e)
        myprint('clear database!')

    def updatedb(self):
        with MyDb() as cx:
            try:
                cx.execute('UPDATE ' + self.dbName +
                           ' SET state =0 WHERE state=-2')
            except Exception as e:
                myprint(e)
        myprint('update db finished!')

    def reset(self):
        with MyDb() as cx:
            try:
                cx.execute("UPDATE " + self.dbName + " SET state=0")
            except Exception as e:
                myprint(e)
        myprint('reset finished')

    def commit(self):
        myprint('commit finished')


def autoReplyMsgs(path, state, finish_state, userName=None, remarkName=None):
    global db

    if not os.path.exists(path):
        return

    with open(path, encoding='utf-8') as fin:
        msgs = json.load(fin)

    keys = list(msgs.keys())

    keys.sort(key=lambda x: int(x))

    for key in keys:
        msg = msgs[key]["msgs"]

        delay = msgs[key]["delay"]

        time.sleep(delay)

        if db.getFriendState(remarkName) != state:
            return

        if type(msg) is list:
            index = random.randint(0, len(msg) - 1)
            reply = msg[index]
        else:
            reply = msg

        if not itchat.send(reply, userName):
            break

    db.setFriendState(remarkName, finish_state)


def add_friend_thread(msg):
    add_lock.acquire()
    key = msg['RecommendInfo']['NickName']

    if key == '':
        key = str(int(time.time()) // (30 * 60))
    try:
        myprint('[*] 添加线程启动', key)
    except Exception as e:
        myprint(e)
        myprint('[*] 添加线程启动')

    time.sleep(random.randint(60, 3 * 60))

    # 五小时重复添加 key保持一致
    timestamp = str(int(time.time()) // (30 * 60))

    key = key + timestamp

    if db.isFriend(key):
        add_lock.release()
        myprint('已在数据库中')
        return
    try:
        if not msg.user.verify():
            myprint('添加失败')
            itchat.send(key, 'filehelper')

    except Exception as e:
        myprint('add error', e)
    finally:
        add_lock.release()


@itchat.msg_register(itchat.content.FRIENDS)
def add_friend(msg):
    threading.Thread(target=add_friend_thread,
                     args=(msg,)).start()


def isKey(content):
    f = open("myJson/keyToCodeKey.json", encoding='utf-8')
    keyToCodeKey = json.load(f)
    f.close()
    myKeyContent = content
    iskey = False
    for key in keyToCodeKey:
        if key == myKeyContent:
            iskey = True
            break
    return iskey


def startDomean():
    def tfun_d():
        self = itchat.get_friends()[0]
        alias = self['Alias']
        if alias == '':
            alias = self['NickName']

        while True:
            time.sleep(random.randint(60 * 5, 60 * 8))
            string = time.strftime('%Y-%m-%d %H-%M-%S',
                                   time.localtime(time.time()))

            flag = False
            try:
                flag = itchat.send(string, 'filehelper')
            except Exception as ex:
                myprint(ex)

            if flag:
                myprint('\n', string, 'aliving', '\n')
            else:
                myprint('\n', string, 'died !', '\n')

    threading.Thread(target=tfun_d).start()
    myprint('[*] 监控线程启动')


def mySetAlias(userName, remarkName):
    set_Alias_lock.acquire()
    try:
        trytimes = 3
        while trytimes > 0:
            time.sleep(random.randint(5, 30))
            if itchat.set_alias(userName, remarkName):
                break
            trytimes -= 1
    except Exception as e:
        myprint(e)
    finally:
        set_Alias_lock.release()


@itchat.msg_register([itchat.content.NOTE])
def receiveHB(msg):
    global addFriendsQueue
    global db

    global set_Alias_lock

    if msg['Text'] == '收到红包，请在手机上查看':
        def fun_r(msg):
            time.sleep(random.randint(2, 5))
            try:
                with open("./myJson/afterRedEnvelope.json", encoding='utf-8') as fin:
                    msgs = json.load(fin)

                    index = random.randint(0, len(msgs) - 1)
                    for i, keyi in enumerate(msgs):
                        if i == index:
                            replyKey = keyi
                            break
                reply = msgs[replyKey]
            except:
                reply = "[色][色][色]哇哦～谢谢宝宝，thankssss[鼓掌]"
            try:
                itchat.send(reply, msg['FromUserName'])
            except Exception as e:
                myprint(e)
            myprint('收到红包')

        threading.Thread(target=fun_r, args=(msg,)).start()
    elif '请先发送朋友验证请求，对方验证通过后，才能聊天' in msg['Content']:
        mySetAlias(msg.user.userName, "AAA_删除" + msg.user.remarkName)
        # msg.user.set_alias('AAA_删除' + msg.user.remarkName)
    elif addFriendContentPattern.match(msg['Text']):
        nickName = addFriendContentPattern.findall(msg['Text'])[0]

        myprint('add friend', nickName)

        userName = msg['FromUserName']

        remarkname = nickName + str(int(time.time()) // (30 * 60))

        if db.isFriend(remarkname):
            return

        mySetAlias(userName, remarkname)

        addFriendsQueue.put({
            'remarkName': remarkname,
            'userName': userName
        })


def addFriend_Consumer():
    global db
    global addFriendsQueue

    def addFriend_Consumer_Thread():
        while True:
            user = addFriendsQueue.get()
            remarkName = user['remarkName']
            userName = user['userName']

            if db.isFriend(remarkName):
                continue

            db.insertFriend(remarkName, -3)

            myprint('send to', remarkName)

            threading.Thread(target=autoReplyMsgs,
                             args=(config.addfriendjson, -3, -1, userName, remarkName)).start()
            time.sleep(20)

    threading.Thread(target=addFriend_Consumer_Thread).start()


def tfun0(name, key):
    db.setFriendState(key, -2)
    db.commit()
    try:
        myprint('state 0 -> state -2', key)
    except Exception as e:
        myprint(e)
        myprint('state 0 -> state -2')

    with open("./myJson/FmsgAndImg.json", encoding='utf-8') as fin:
        msgs = json.load(fin)

    index = random.randint(0, len(msgs) - 1)
    for i, keyi in enumerate(msgs):
        if i == index:
            msg = msgs[keyi]
            break

    index = random.randint(0, len(msg['img']) - 1)

    for i, img in enumerate(msg['img']):
        if i == index:
            replyImg = msg['img'][img]
            break
    msgText = msg['msg']

    time.sleep(random.randint(10, 30))

    mySendPic(name, replyImg)
    time.sleep(1)
    itchat.send(msgText, name)

    db.setFriendState(key, 2)
    db.commit()

    user = itchat.search_friends(userName=name)

    threading.Thread(target=autoReplyMsgs, args=(
        config.waitpicjson, 2, 2, user.userName, key)).start()

    try:
        myprint('state 0 -> state 2', key)
    except Exception as e:
        myprint('state 0 -> state 2')


def fun3(name, key):
    db.setFriendState(key, -2)
    db.commit()
    try:
        myprint('state 3 -> state -2', key)
    except Exception as e:
        myprint('state 3 -> state -2')

    with open('./myJson/MsgFour.json', encoding='utf-8') as fin:
        msgs = json.load(fin)
    index = random.randint(0, len(msgs) - 1)
    replyMsg = None
    for i, keyi in enumerate(msgs):
        if i == index:
            replyMsg = msgs[keyi]
            break
    time.sleep(random.randint(10, 20))

    itchat.send(replyMsg, name)
    time.sleep(random.randint(30, 60))
    with open('./myJson/SmsgAndImg.json', encoding='utf-8') as fin:
        msgs = json.load(fin)
        index = random.randint(0, len(msgs) - 1)
        for i, k in enumerate(msgs):
            if index == i:
                replyMsg = msgs[k]

    mySendPic(name, replyMsg['img'])

    time.sleep(1)
    itchat.send(replyMsg['msg'], name)

    db.setFriendState(key, 4)
    db.commit()
    try:
        myprint('state 3 -> state 4', key)
    except Exception as e:
        myprint('state 3 -> state 4')

    try:
        myprint(key, '等待数字')
    except:
        myprint('等待数字')

    time.sleep(5 * 60)
    if db.getFriendState(key) == 4:
        with open('./myJson/noMsgTips.json', encoding='utf-8') as fin:
            msgs = json.load(fin)
            index = random.randint(0, len(msgs) - 1)
            for i, k in enumerate(msgs):
                if index == i:
                    replyMsg = msgs[k]
                    break
        itchat.send(replyMsg, name)
        try:
            myprint('state 3 thread end', key)
        except Exception as e:
            myprint('state 3 thread end')


def fun4(name, key):
    db.setFriendState(key, -2)
    db.commit()
    try:
        myprint('state 4 -> state -2', key)
    except:
        myprint('state 4 -> state -2')

    with open('./myJson/TenSecMsg.json', encoding='utf-8') as fin:
        msgs = json.load(fin)
    index = random.randint(0, len(msgs) - 1)
    for i, k in enumerate(msgs):
        if i == index:
            replyMsg = msgs[k]
            break
    index = random.randint(0, len(replyMsg) - 1)
    for i, k in enumerate(replyMsg):
        if i == index:
            m = replyMsg[k]
            break
    replyImg = m['img']
    replyMsgs = m['msg']
    time.sleep(random.randint(10, 30))

    mySendPic(name, replyImg)

    time.sleep(1)
    for i in range(1, len(replyMsgs)):
        k = 'msg' + str(i)

        try:
            myprint('send msg ', i, 'to ', key)
        except:
            myprint('send msg ', i, 'to ')

        if k in replyMsgs.keys():
            if replyMsgs[k] != "":
                try:
                    time.sleep(random.randint(20, 30))
                    itchat.send(replyMsgs[k], name)
                except Exception as e:
                    myprint(e)
    db.setFriendTime(key)
    db.commit()
    db.setFriendState(key, 5)
    db.commit()
    try:
        myprint('state 4 -> state 5', key)
    except:
        myprint('state 4 -> state 5')


def groupChat():
    global db
    global robotChat

    def sub_fun():
        friends = db.getFriends([-1, 0, 2])
        for friendid in friends:
            time.sleep(60)
            if not robotChat:
                continue
            state = db.getFriendState(friendid)

            myprint('send to', friendid)

            users = itchat.search_friends(remarkName=friendid)
            if not users:
                continue
            user = None
            for x in users:
                if x.remarkName == friendid:
                    user = x
                    break

            if user is None:
                continue
            if state == -1:
                autoReplyMsgs(config.dailycheckjson, -1, -
                1, user.userName, friendid)
            elif state == 2:
                autoReplyMsgs(config.dailycheckjson, 2, -
                1, user.userName, friendid)
            elif state == 0:
                autoReplyMsgs(config.dailycheckjson, 0, -
                1, user.userName, friendid)
        itchat.send('auto chat finished!!!!')

    threading.Thread(target=sub_fun).start()


@itchat.msg_register([itchat.content.TEXT, itchat.content.PICTURE])
def fun(msg):
    global robotChat
    global db
    if msg['ToUserName'] == 'filehelper':
        print(msg.text)
        if msg.text.startswith('autochat'):
            if msg.text[9:] == 'on':
                itchat.send('autochat on finished!', 'filehelper')
                robotChat = True
                groupChat()
            else:
                itchat.send('autochat off finished!', 'filehelper')
                robotChat = False
        return

    user = msg.user

    user.update()

    key = user['RemarkName']

    userid = user['UserName']
    content = msg['Content']

    if key == '':
        if user['Alias'] == '':
            key = user['NickName']
            if key == '':
                key = str(int(time.time()))
        else:
            key = user['Alias']

        timestamp = str(int(time.time()) // (30 * 60))
        key += timestamp

        mySetAlias(userid, key)
        # itchat.set_alias(userid, key)
        try:
            myprint('设置备注', key)
        except:
            myprint('设置备注')

        db.insertFriend(key, -1)
        db.commit()
        try:
            myprint('插入', key)
            myprint('添加 2 ', key)
        except:
            myprint('插入')
            myprint('添加 2 ')
    if not db.isFriend(key):
        db.insertFriend(key, -1)
        db.commit()
        try:
            myprint('添加 2 ', key)
        except:
            myprint('添加 2 ')

    state = db.getFriendState(key)

    if state == -1 or state == -3 or state == -4:

        db.setFriendState(key, 1)
        state = 1
        try:
            myprint('state -1 -> 1,', key)
        except:
            myprint('state -1 -> 1,')

    if state == 0:
        if isKey(content):
            try:
                myprint('[*] 收到关键字', key)
            except:
                myprint('[*] 收到关键字')
            db.addFriendState(key)
            db.commit()
            try:
                myprint('state 0 -> state 1', key)
            except:
                myprint('state 0 -> state 1')

            state += 1

    if state == 1:

        threading.Thread(target=tfun0, args=(userid, key)).start()

    elif state == 2:  # 等待图图片
        if msg['Type'] != 'Picture':
            return
        db.addFriendState(key)
        db.commit()
        try:
            myprint('state 2 -> state 3', key)
        except:
            myprint('state 2 -> state 3')
        state = 3

    if state == 3:  # 收到图片后

        threading.Thread(target=fun3, args=(userid, key)).start()
    elif state == 4:  # 等待数字
        if msg['Type'] != 'Text':
            return
        num = -1
        try:
            items = re.search('\d+|[一二三四五六七八九]+', content)
            if items:
                num = random.randint(1, 22)
                myprint(content)
        except:
            myprint('[*] 转化失败')
        if num < 1 or num > 22:
            with open('./myJson/NotNumTips.json', encoding='utf-8') as fin:
                msgs = json.load(fin)
                index = random.randint(0, len(msgs) - 1)
                for i, k in enumerate(msgs):
                    if i == index:
                        replyMsg = msgs[k]
                        break
            itchat.send(replyMsg, userid)

            try:
                myprint('no num', key)
            except:
                myprint('no num')
            return

        threading.Thread(target=fun4, args=(userid, key)).start()
    elif state == 5:
        def sub_fun_5(userid):

            time.sleep(random.randint(10, 30))

            with open('myJson/weekAgain.json', encoding='utf-8') as fin:
                msgs = json.load(fin)
                randi = random.randint(0, len(msgs) - 1)
                for i, k in enumerate(msgs):
                    if i == randi:
                        msg = msgs[k]
            itchat.send(msg, userid)

        def sub_fun_2(msg, key):
            db.setFriendState(key, -2)
            autoReplyMsgs(config.afterTarotjson, -
            2, -2, msg.user.userName, key)
            time.sleep(15 * 60)
            db.setFriendState(key, 5)

        if db.getFriendTime(key) is not None and int(time.time()) - db.getFriendTime(key) < 15 * 60:
            threading.Thread(target=sub_fun_2, args=(msg, key)).start()
        elif isKey(content):
            threading.Thread(target=sub_fun_5, args=(userid,)).start()


def myQRCallback(uuid, status, qrcode):
    global qrtimes
    global qrpath
    qrtimes -= 1
    if qrtimes < 0:
        if os.path.exists(qrpath):
            os.remove(qrpath)
        os._exit(0)
    with open(qrpath, 'wb') as f:
        f.write(qrcode)


def clearnDiedPeople():
    db.updatedb()


def myquit():
    global qrpath
    if os.path.exists(qrpath):
        os.remove(qrpath)
    os._exit(0)


def eachWeekCheck():
    def tfun_e():
        while True:
            time.sleep(60 * 2)

            name = db.getWeekFriend()
            myprint('每周发送线程启动,选择随机用户')

            if name == None:
                continue

            db.setFriendState(name, 0)
            db.commit()
            myprint('每周发送线程启动，更新选择随机用户状态')

            users = itchat.search_friends(remarkName=name)
            for user in users:
                if user.remarkName == name:
                    threading.Thread(target=autoReplyMsgs,
                                     args=(config.eachweekjson, 0, 0, user.userName, name)).start()
                    break

    threading.Thread(target=tfun_e).start()
    myprint('[*] 每周发送线程启动')


def myloginCallback():
    global qrpath
    if os.path.exists(qrpath):
        os.remove(qrpath)


def recoverFriends_Thread():
    global db

    def sub_fun():
        myprint('recover thread start')

        friends = itchat.get_friends()
        for friend in friends:
            if friend.remarkName == '':
                remarkName = friend.nickName + \
                             str(int(time.time()) // (30 * 60))

                mySetAlias(friend.userName, remarkName)

                time.sleep(random.randint(5, 10))

                myprint('add ', remarkName)

                db.insertFriend(remarkName, 5)
            elif not db.isFriend(friend.remarkName):
                myprint('add ', friend.remarkName)

                db.insertFriend(friend.remarkName, 5)

    threading.Thread(target=sub_fun).start()


def authThread():
    def sub_fun():
        while True:
            time.sleep(60)
            try:
                requests.get("http://rzwei.cn:5051/run")
            except:
                myquit()

    threading.Thread(target=sub_fun).start()


def run(path):
    global qrpath
    global db

    # checkServer()

    qrpath = path

    os.chdir(config.basepath)

    print('base dir:', os.getcwd())

    itchat.auto_login(hotReload=False, qrCallback=myQRCallback,
                      exitCallback=myquit, loginCallback=myloginCallback)

    friendsList = itchat.get_friends(update=False)

    myself = friendsList[0]

    db = dbHelper_mysql(str(myself['Uin']))

    clearnDiedPeople()

    startDomean()

    eachWeekCheck()

    addFriend_Consumer()

    #authThread()
    # recoverFriends_Thread()

    itchat.run()


if __name__ == '__main__':
    run('qr.png')
