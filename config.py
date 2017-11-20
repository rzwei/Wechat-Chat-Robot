import json

dbaddress = '127.0.0.1'
basepath = 'C:/clients/weixinbot_flask-release'
dbusername = 'weixin'
dbpassword = 'weixin'
eachweekjson = './myJson/eachWeekTips.json'
addfriendjson = './myJson/AddFriend.json'
waitpicjson = './myJson/PictureNoReply.json'
dailycheckjson = './myJson/dailycheck.json'
afterTarotjson = './myJson/afterTarot.json'
imagepath = './images/'
picname = ['a.png', 'b.png', 'c.png']

host = "127.0.0.1"
port = '5000'
account = 'admin'
password = "admin2"
alvieCount = 1
d = None
try:
    with open('config.json', encoding='utf-8') as fin:
        d = json.load(fin)
except Exception as e:
    print('open config.json error', e)
if d:
    if 'dbaddress' in d:
        dbaddress = d['dbaddress']
    if 'basepath' in d:
        basepath = d['basepath']
    if 'dbusername' in d:
        dbusername = d['dbusername']
    if 'dbpassword' in d:
        dbpassword = d['dbpassword']
    if 'eachweekjson' in d:
        eachweekjson = d['eachweekjson']
    if 'addfriendjson' in d:
        addfriendjson = d['addfriendjson']
    if 'waitpicjson' in d:
        waitpicjson = d['waitpicjson']
    if 'dailycheckjson' in d:
        dailycheckjson = d['dailycheckjson']
    if 'afterTarotjson' in d:
        afterTarotjson = d['afterTarotjson']
    if 'account' in d:
        account = d['account']
    if 'password' in d:
        password = d['password']
    if 'host' in d:
        host = d['host']
    if 'port' in d:
        port = d['port']
    if 'aliveCount' in d:
        aliveCount = d['aliveCount']
    if 'imagepath' in d:
        imagepath = d['imagepath']
    if 'picname' in d:
        picname = d['picname']
