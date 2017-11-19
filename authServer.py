from flask import Flask, request

import config

app = Flask(__name__)


@app.route('/run', methods=["GET", "POST"])
def run():
    print(request.host)
    return 'true'


if __name__ == '__main__':
    app.run(port=config.authPort, host=config.authHost)
