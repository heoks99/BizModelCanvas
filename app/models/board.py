from app import db
from datetime import datetime


class BoardPost(db.Model):
    __tablename__ = 'board_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, default='')
    category = db.Column(db.String(20), nullable=False, default='notice')  # notice | manual
    is_pinned = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name = db.Column(db.String(300))
    file_data = db.Column(db.LargeBinary)
    file_mime = db.Column(db.String(100))
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref='board_posts')

    def __repr__(self):
        return f'<BoardPost {self.id}: {self.title[:30]}>'
