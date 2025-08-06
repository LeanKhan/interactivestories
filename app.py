"""
Play PPT-PDF Interactive Stories

Author: Emmanuel Segun-Lean
"""

import os
from flask import Flask, render_template, flash, request, redirect, send_from_directory, url_for
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pptx', 'ppt'}

app = Flask(__name__)

app.secret_key = b'supersecretkeyomgs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

stories = [
        {
            "id": 1,
            "title": "The Haunted Lake",
            "author": "Jane Doe",
            "tags": ["Horror", "Sad", "Short"],
            "image_url": "https://placehold.co/400x300"
        },
        {
            "id": 2,
            "title": "Sunlight & Shadows",
            "author": "John Smith",
            "tags": ["Drama", "Poetic"],
            "image_url": "https://placehold.co/400x300"
        },
         {
            "id": 3,
            "title": "My time as a street sweeper",
            "author": "Carla Jepsen",
            "tags": ["Drama", "Funny"],
            "image_url": "https://placehold.co/400x300"
        }
    ]


@app.route('/')
def index(name=None):
    return render_template('index.html', stories=stories)

@app.route('/stories/<id>')
def view_story(id=None):
    return render_template('view_story.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

@app.route('/processed/<name>')
def download_processed_file(name):
    return send_from_directory("processed", name)

@app.route("/download/<name>")
def download_page(name):
    return render_template('download.html', filename=name)


if __name__ == "__main__":
    # Quick test configuration. Please use proper Flask configuration options
    # in production settings, and use a separate file or environment variables
    # to manage the secret key!
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.debug = True
    app.run()
