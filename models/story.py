from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

file_tags = db.Table(
    'file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('story.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

"""
	Story Class
"""
class Story(db.Model):	
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    author = db.Column(db.String(255))
    thumbnail_filename = db.Column(db.String(255))
    thumbnail_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    tags = db.relationship('Tag', secondary=file_tags, back_populates='stories')

    def __repr__(self):
        return f"<Story {self.title}>"


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    stories = db.relationship('Story', secondary=file_tags, back_populates='tags')