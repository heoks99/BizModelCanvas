from app import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    organization = db.Column(db.String(100))
    business_manager = db.Column(db.String(100))
    project_manager = db.Column(db.String(100))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=False)  # 전체 공개 여부
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = db.relationship('Analysis', backref='project', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'


class Analysis(db.Model):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    module_type = db.Column(db.String(50), nullable=False)
    # module_type: pestel, five_forces, swot, ansoff, horizons, ogsm, result_report
    input_data = db.Column(db.Text)   # JSON 문자열로 저장
    ai_result = db.Column(db.Text)    # Claude AI 분석 결과
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Analysis {self.module_type} - Project {self.project_id}>'
