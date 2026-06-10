from app import db
from datetime import datetime


class QnA(db.Model):
    __tablename__ = 'qna'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    ai_answer = db.Column(db.Text)
    ai_pending = db.Column(db.Boolean, default=False)   # AI 답변 생성 중
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    file_name = db.Column(db.String(300))
    file_data = db.Column(db.LargeBinary)
    file_mime = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref='qnas')
    project = db.relationship('Project', backref='qnas')
    comments = db.relationship('QnAComment', backref='qna', cascade='all, delete-orphan',
                               order_by='QnAComment.created_at')

    def __repr__(self):
        return f'<QnA {self.id}: {self.title[:30]}>'


class QnAComment(db.Model):
    __tablename__ = 'qna_comments'

    id = db.Column(db.Integer, primary_key=True)
    qna_id = db.Column(db.Integer, db.ForeignKey('qna.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    ai_answer = db.Column(db.Text)
    ai_pending = db.Column(db.Boolean, default=False)   # AI 답변 생성 중
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='qna_comments')

    def __repr__(self):
        return f'<QnAComment {self.id}>'


class QnAAnalysisResult(db.Model):
    """질문 유형 AI 분석 결과 저장"""
    __tablename__ = 'qna_analysis_results'

    id = db.Column(db.Integer, primary_key=True)
    result_json = db.Column(db.Text, nullable=False)
    analyzed_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<QnAAnalysisResult {self.id} ({self.analyzed_count}건)>'
