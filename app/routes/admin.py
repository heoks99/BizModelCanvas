from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.models.project import Project

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('관리자 권한이 필요합니다.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    stats = {
        'total':    User.query.count(),
        'pending':  User.query.filter_by(status='pending').count(),
        'active':   User.query.filter_by(status='active').count(),
        'inactive': User.query.filter_by(status='inactive').count(),
        'projects': Project.query.count(),
    }
    return render_template('admin/index.html', users=users, stats=stats)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    projects = Project.query.filter_by(owner_id=user_id).all()
    return render_template('admin/user_detail.html', user=user, projects=projects)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'active'
    db.session.commit()
    return jsonify({'ok': True, 'status': 'active'})


@admin_bp.route('/users/<int:user_id>/set_status', methods=['POST'])
@login_required
@admin_required
def set_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'ok': False, 'msg': '자기 자신의 상태는 변경할 수 없습니다.'})
    status = request.json.get('status')
    if status not in ('active', 'inactive', 'pending'):
        return jsonify({'ok': False, 'msg': '잘못된 상태값입니다.'})
    user.status = status
    db.session.commit()
    return jsonify({'ok': True, 'status': status})


@admin_bp.route('/users/<int:user_id>/set_role', methods=['POST'])
@login_required
@admin_required
def set_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'ok': False, 'msg': '자기 자신의 역할은 변경할 수 없습니다.'})
    role = request.json.get('role')
    if role not in ('admin', 'member'):
        return jsonify({'ok': False, 'msg': '잘못된 역할값입니다.'})
    user.role = role
    db.session.commit()
    return jsonify({'ok': True, 'role': role})


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        full_name    = request.form.get('full_name', '').strip()
        email        = request.form.get('email', '').strip()
        organization = request.form.get('organization', '').strip()
        job_title    = request.form.get('job_title', '').strip()
        role         = request.form.get('role', 'member')
        status       = request.form.get('status', 'active')
        new_pw       = request.form.get('new_password', '').strip()

        if not email:
            flash('이메일은 필수입니다.', 'error')
        elif email != user.email and User.query.filter_by(email=email).first():
            flash('이미 사용 중인 이메일입니다.', 'error')
        else:
            user.full_name    = full_name
            user.email        = email
            user.organization = organization
            user.job_title    = job_title
            user.role         = role
            user.status       = status
            if new_pw:
                user.set_password(new_pw)
            db.session.commit()
            flash(f'{user.username} 정보가 수정되었습니다.', 'success')
            return redirect(url_for('admin.index'))

    return render_template('admin/edit_user.html', user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('자기 자신은 삭제할 수 없습니다.', 'error')
        return redirect(url_for('admin.index'))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'"{username}" 계정이 삭제되었습니다.', 'success')
    return redirect(url_for('admin.index'))
