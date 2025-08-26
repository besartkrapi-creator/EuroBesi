from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "EuroBesi App Final – Deploy i gatshëm!"
