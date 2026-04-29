import markupsafe
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요합니다.'

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @app.template_filter('nl2br')
    def nl2br(value):
        return markupsafe.Markup(markupsafe.escape(value).replace('\n', markupsafe.Markup('<br>')))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.modules import modules_bp
    from app.routes.search import search_bp
    from app.routes.qna import qna_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(qna_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_sidebar_orgs():
        if current_user.is_authenticated:
            from app.models.project import Project
            projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.updated_at.desc()).all()
            orgs = {}
            for p in projects:
                key = p.organization or '미지정'
                orgs.setdefault(key, []).append(p)
            return {'sidebar_orgs': orgs}
        return {'sidebar_orgs': {}}

    with app.app_context():
        db.create_all()

    return app
