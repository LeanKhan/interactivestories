"""
Play PPT-PDF Interactive Stories

Author: Emmanuel Segun-Lean
"""

from models.story import Story, Tag
from models.user import User
import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, send_from_directory, request, flash, url_for

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import (LoginManager, current_user, login_user,
                         logout_user)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from wtforms import FileField
import logging
from logging.handlers import RotatingFileHandler

from models import db
from services.azure_storage import AzureBlobStorage

# Load environment variables
load_dotenv()


ALLOWED_EXTENSIONS = {'pptx', 'ppt'}

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stories.db"
app.config["SECRET_KEY"] = "supersecretkeyomg"

# Initialize db with app
db.init_app(app)

# Import models after db is initialized

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # type: ignore

# Azure Blob Storage Configuration
app.config["AZURE_STORAGE_CONNECTION_STRING"] = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING")
app.config["AZURE_CONTAINER_NAME"] = os.getenv(
    "AZURE_CONTAINER_NAME", "pdf-stories")

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
app.config["FILE_UPLOAD_FOLDER"] = os.path.join(
    app.config["UPLOAD_FOLDER"], app.config["FILE_UPLOAD_FOLDER_RELATIVE"])
app.config["THUMBNAIL_UPLOAD_FOLDER"] = os.path.join(
    app.config["UPLOAD_FOLDER"], app.config["THUMBNAIL_UPLOAD_FOLDER_RELATIVE"])

# Create local folders only if Azure is not configured (fallback mode)
if not azure_storage:
    os.makedirs(app.config["FILE_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_UPLOAD_FOLDER"], exist_ok=True)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'


class StoryModelView(ModelView):
    # column_list = ("id", "filename", "title", "tags", "uploaded_at")
    # form_columns = ("file_upload", "title", "description", "author", "created_at", "tags")

    form_excluded_columns = (
        'filename', 'path', 'thumbnail_filename', 'thumbnail_path', 'uploaded_at')

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
                # Store blob name instead of local path
                model.path = upload_result['blob_name']
            else:
                # Fallback to local storage
                filename = secure_filename(file_data.filename)
                save_path = os.path.join(
                    app.config["FILE_UPLOAD_FOLDER"], filename)
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
                # Store blob name instead of local path
                model.thumbnail_path = upload_result['blob_name']
            else:
                # Fallback to local storage
                thumb_filename = secure_filename(thumb_data.filename)
                thumb_path = os.path.join(
                    app.config["THUMBNAIL_UPLOAD_FOLDER"], thumb_filename)
                thumb_data.save(thumb_path)
                model.thumbnail_filename = thumb_filename
                model.thumbnail_path = thumb_path


# Auth Routes
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated


admin = Admin(app, name="Local CMS", template_mode="bootstrap3",
              index_view=MyAdminIndexView())
admin.add_view(StoryModelView(Story, db.session))
admin.add_view(ModelView(Tag, db.session))
admin.add_view(SecureModelView(User, db.session))

# Set up logging
if not app.debug:
    file_handler = RotatingFileHandler('/srv/interactivestories/logs/flask.log',
                                       maxBytes=10240000,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Interactive Stories Site startup')


@app.route('/')
def index():
    stories = Story.query.filter().all()

    for story in stories:
        if azure_storage:
            # Use Azure Blob Storage URLs
            story.thumbnail_url = azure_storage.get_blob_url(
                story.thumbnail_path)
            story.pdf_url = azure_storage.get_blob_url(story.path)
        else:
            # Use local storage URLs
            story.thumbnail_url = f"/{app.config['UPLOAD_FOLDER_RELATIVE']}/{app.config['THUMBNAIL_UPLOAD_FOLDER_RELATIVE']}/{story.thumbnail_filename}"
            story.pdf_url = f"/{app.config['UPLOAD_FOLDER_RELATIVE']}/{app.config['FILE_UPLOAD_FOLDER_RELATIVE']}/{story.filename}"

    return render_template('index.html', stories=stories)


@app.route('/stories/<id>')
def view_story(_id):
    _story = Story.query.filter(Story.id == _id).first_or_404()

    if azure_storage:
        # Use Azure Blob Storage URL
        _story.pdf_url = azure_storage.get_blob_url(_story.path)
    else:
        # Use local storage URL
        _story.pdf_url = f"/{app.config['UPLOAD_FOLDER_RELATIVE']}/{app.config['FILE_UPLOAD_FOLDER_RELATIVE']}/{_story.filename}"

    return render_template('view_story.html', story=_story)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/processed/<name>')
def download_processed_file(name):
    return send_from_directory("processed", name)


@app.route("/download/<name>")
def download_page(name):
    return render_template('download.html', filename=name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Catch all unhandled exceptions


@app.errorhandler(Exception)
def handle_exception(e):
    """error handling"""

    if isinstance(e, HTTPException):
        return e

    app.logger.exception("Unhandled exception")
    return {"error": "Internal server error"}, 500


if __name__ == "__main__":
    # Quick test configuration. Please use proper Flask configuration options
    # in production settings, and use a separate file or environment variables
    # to manage the secret key!
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    with app.app_context():
        db.create_all()
        # admin_user = User(username='admin')
        # admin_user.set_password('yourpassword')
        # db.session.add(admin_user)
        # db.session.commit()

    app.debug = False
    app.run(host='0.0.0.0')
