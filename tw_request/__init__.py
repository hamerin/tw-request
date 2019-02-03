from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def intro():
    return render_template('index.html')

@app.route("/generic.html")
def generic():
    return render_template('generic.html')

@app.route("/elements.html")
def elements():
    return render_template('elements.html')