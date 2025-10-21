"""
Play PPT-PDF Interactive Stories

Author: Emmanuel Segun-Lean
"""

import os
from flask import Flask, render_template, flash, request, redirect, send_from_directory, url_for
from werkzeug.utils import secure_filename
from flask_admin import Admin, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from models.story import Tag, db, Story

from flask_admin import Admin
from wtforms import FileField


ALLOWED_EXTENSIONS = {'pptx', 'ppt'}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stories.db"
app.config["SECRET_KEY"] = "supersecretkeyomg"

app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")

app.config["UPLOAD_FOLDER_RELATIVE"] = 'uploads'

app.config["FILE_UPLOAD_FOLDER_RELATIVE"] = "pdfs"
app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"] = "thumbnails"

app.config["FILE_UPLOAD_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], app.config["FILE_UPLOAD_FOLDER_RELATIVE"])
app.config["THUMBNAIL_UPLOAD_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"])

os.makedirs(app.config["FILE_UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["THUMBNAIL_UPLOAD_FOLDER"], exist_ok=True)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

db.init_app(app)

class StoryModelView(ModelView):
    # column_list = ("id", "filename", "title", "tags", "uploaded_at")
    # form_columns = ("file_upload", "title", "description", "author", "created_at", "tags")
    
    form_excluded_columns = ('filename', 'path', 'thumbnail_filename', 'thumbnail_path', 'uploaded_at')

    # Add file upload field    
    def scaffold_form(self):
        form_class = super(StoryModelView, self).scaffold_form()
        form_class.file_upload = FileField("Main File")
        form_class.thumbnail_upload = FileField("Thumbnail (optional)")
        return form_class

    # Handle file saving
    def on_model_change(self, form, model, is_created):
        file_data = form.file_upload.data
        if file_data:
            filename = secure_filename(file_data.filename)
            save_path = os.path.join(app.config["FILE_UPLOAD_FOLDER"], filename)
            file_data.save(save_path)
            model.filename = filename
            model.path = save_path

        # Handle thumbnail upload
        thumb_data = form.thumbnail_upload.data
        if thumb_data:
            thumb_filename = secure_filename(thumb_data.filename)
            thumb_path = os.path.join(app.config["THUMBNAIL_UPLOAD_FOLDER"], thumb_filename)
            thumb_data.save(thumb_path)
            model.thumbnail_filename = thumb_filename
            model.thumbnail_path = thumb_path

admin = Admin(app, name="Local CMS", template_mode="bootstrap3")
admin.add_view(StoryModelView(Story, db.session))
admin.add_view(ModelView(Tag, db.session))

@app.route('/')
def index(name=None):
    stories = Story.query.filter().all()
    
    for story in stories:
        story.thumbnail_url = f"/{ app.config['UPLOAD_FOLDER_RELATIVE'] }/{app.config['THUMBNAIL_UPLOAD_FOLDER_RELATIVE']}/{ story.thumbnail_filename}"
        story.pdf_url = f"/{ app.config['UPLOAD_FOLDER_RELATIVE'] }/{app.config['FILE_UPLOAD_FOLDER_RELATIVE']}/{ story.filename}"

    return render_template('index.html', stories=stories)

@app.route('/stories/<id>')
def view_story(id):
    _story = Story.query.filter(Story.id == id).first_or_404()
    _story.pdf_url = f"/{ app.config['UPLOAD_FOLDER_RELATIVE'] }/{app.config['FILE_UPLOAD_FOLDER_RELATIVE']}/{ _story.filename}"

    return render_template('view_story.html', story=_story)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
    
    with app.app_context():
        db.create_all()

    app.debug = True
    app.run(host='0.0.0.0')
