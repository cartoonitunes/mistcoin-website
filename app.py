from flask import Flask, send_from_directory, redirect, url_for

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def catch_all(path):
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
