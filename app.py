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
from services.azure_storage import AzureBlobStorage
from dotenv import load_dotenv

from flask_admin import Admin
from wtforms import FileField

# Load environment variables
load_dotenv()


ALLOWED_EXTENSIONS = {'pptx', 'ppt'}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stories.db"
app.config["SECRET_KEY"] = "supersecretkeyomg"

# Azure Blob Storage Configuration
app.config["AZURE_STORAGE_CONNECTION_STRING"] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
app.config["AZURE_CONTAINER_NAME"] = os.getenv("AZURE_CONTAINER_NAME", "pdf-stories")

# Blob folder names
app.config["FILE_UPLOAD_FOLDER_RELATIVE"] = "pdfs"
app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"] = "thumbnails"

# Initialize Azure Blob Storage service
azure_storage = None
if app.config["AZURE_STORAGE_CONNECTION_STRING"]:
    azure_storage = AzureBlobStorage(
        connection_string=app.config["AZURE_STORAGE_CONNECTION_STRING"],
        container_name=app.config["AZURE_CONTAINER_NAME"]
    )

# Legacy local storage configuration (fallback)
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
app.config["UPLOAD_FOLDER_RELATIVE"] = 'uploads'
app.config["FILE_UPLOAD_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], app.config["FILE_UPLOAD_FOLDER_RELATIVE"])
app.config["THUMBNAIL_UPLOAD_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"])

# Create local folders only if Azure is not configured (fallback mode)
if not azure_storage:
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
            if azure_storage:
                # Upload to Azure Blob Storage
                upload_result = azure_storage.upload_file(
                    file_data=file_data,
                    folder=app.config["FILE_UPLOAD_FOLDER_RELATIVE"]
                )
                model.filename = upload_result['filename']
                model.path = upload_result['blob_name']  # Store blob name instead of local path
            else:
                # Fallback to local storage
                filename = secure_filename(file_data.filename)
                save_path = os.path.join(app.config["FILE_UPLOAD_FOLDER"], filename)
                file_data.save(save_path)
                model.filename = filename
                model.path = save_path

        # Handle thumbnail upload
        thumb_data = form.thumbnail_upload.data
        if thumb_data:
            if azure_storage:
                # Upload to Azure Blob Storage
                upload_result = azure_storage.upload_file(
                    file_data=thumb_data,
                    folder=app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"]
                )
                model.thumbnail_filename = upload_result['filename']
                model.thumbnail_path = upload_result['blob_name']  # Store blob name instead of local path
            else:
                # Fallback to local storage
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
        if azure_storage:
            # Use Azure Blob Storage URLs
            story.thumbnail_url = azure_storage.get_blob_url(story.thumbnail_path)
            story.pdf_url = azure_storage.get_blob_url(story.path)
        else:
            # Use local storage URLs
            story.thumbnail_url = f"/{ app.config['UPLOAD_FOLDER_RELATIVE'] }/{app.config['THUMBNAIL_UPLOAD_FOLDER_RELATIVE']}/{ story.thumbnail_filename}"
            story.pdf_url = f"/{ app.config['UPLOAD_FOLDER_RELATIVE'] }/{app.config['FILE_UPLOAD_FOLDER_RELATIVE']}/{ story.filename}"

    return render_template('index.html', stories=stories)

@app.route('/stories/<id>')
def view_story(id):
    _story = Story.query.filter(Story.id == id).first_or_404()

    if azure_storage:
        # Use Azure Blob Storage URL
        _story.pdf_url = azure_storage.get_blob_url(_story.path)
    else:
        # Use local storage URL
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
