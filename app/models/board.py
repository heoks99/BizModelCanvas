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
    comments = db.relationship('BoardComment', backref='post',
                               cascade='all, delete-orphan',
                               order_by='BoardComment.created_at')

    def __repr__(self):
        return f'<BoardPost {self.id}: {self.title[:30]}>'


class BoardComment(db.Model):
    __tablename__ = 'board_comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('board_posts.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='board_comments')

    def __repr__(self):
        return f'<BoardComment {self.id} on post {self.post_id}>'


class BoardReadStatus(db.Model):
    """사용자별 게시글 읽음 여부"""
    __tablename__ = 'board_read_status'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('board_posts.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='uq_board_read_user_post'),
    )
