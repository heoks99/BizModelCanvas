import re
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.models.project import Project
from app.models.qna import QnA, QnAComment

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
        'qna_total':    QnA.query.count(),
        'qna_answered': QnA.query.filter(QnA.ai_answer.isnot(None)).count(),
        'qna_comments': QnAComment.query.count(),
    }
    return render_template('admin/index.html', users=users, stats=stats)


# ── QnA 대시보드 ──────────────────────────────────────────────
@admin_bp.route('/qna')
@login_required
@admin_required
def qna_dashboard():
    from sqlalchemy import func

    total     = QnA.query.count()
    answered  = QnA.query.filter(QnA.ai_answer.isnot(None)).count()
    pending   = QnA.query.filter_by(ai_pending=True).count()
    no_answer = QnA.query.filter(QnA.ai_answer.is_(None), QnA.ai_pending == False).count()
    comments  = QnAComment.query.count()

    # 사용자별 질문 수
    user_stats = (
        db.session.query(
            User.id,
            User.username,
            User.full_name,
            User.organization,
            func.count(QnA.id).label('qna_count'),
        )
        .outerjoin(QnA, User.id == QnA.owner_id)
        .group_by(User.id)
        .order_by(func.count(QnA.id).desc())
        .all()
    )

    recent_qnas = QnA.query.order_by(QnA.created_at.desc()).limit(30).all()

    stats = dict(
        total=total, answered=answered, pending=pending,
        no_answer=no_answer, comments=comments,
    )
    return render_template('admin/qna.html',
                           stats=stats,
                           user_stats=user_stats,
                           recent_qnas=recent_qnas)


# ── QnA AI 분석 (비동기 JSON) ─────────────────────────────────
@admin_bp.route('/qna/analyze', methods=['POST'])
@login_required
@admin_required
def analyze_qna():
    import anthropic

    qnas = QnA.query.order_by(QnA.created_at.desc()).limit(150).all()
    if not qnas:
        return jsonify({'ok': False, 'msg': '분석할 질의응답이 없습니다.'})

    lines = []
    for i, q in enumerate(qnas, 1):
        line = f"[Q{i}] {q.title} | {q.content[:200].replace(chr(10), ' ')}"
        if q.ai_answer:
            plain = re.sub(r'<[^>]+>', '', q.ai_answer)[:150].replace('\n', ' ')
            line += f" | AI: {plain}"
        lines.append(line)
    qna_text = '\n'.join(lines)

    system = (
        "당신은 SaaS 서비스 개선 분석 전문가입니다. "
        "반드시 순수 JSON만 출력하세요. 코드블록(```) 없이 JSON만."
    )
    user_msg = f"""아래 질의응답 {len(qnas)}건을 분석하여 JSON을 출력하세요.

{qna_text}

출력 형식 (반드시 이 구조):
{{
  "summary": "전체 질의응답 동향을 2~3문장으로 요약",
  "categories": [
    {{
      "name": "카테고리명",
      "count": 건수(숫자),
      "icon": "이모지",
      "description": "이 유형 질문들의 공통 패턴과 사용자 니즈",
      "examples": ["대표 질문 제목1", "대표 질문 제목2"],
      "improvement": "서비스 개선 제안 1~2문장"
    }}
  ],
  "top_issues": ["주요 이슈/니즈 항목 (최대 5개)"],
  "recommendations": ["기능 개선 권고사항 (최대 5개)"]
}}"""

    raw = ''
    try:
        client = anthropic.Anthropic(api_key=current_app.config.get('ANTHROPIC_API_KEY', ''))
        message = client.messages.create(
            model='claude-opus-4-8',
            max_tokens=3000,
            thinking={'type': 'adaptive'},
            system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
            messages=[{'role': 'user', 'content': user_msg}],
        )
        raw = next(b.text for b in message.content if b.type == 'text').strip()
        # 코드블록 제거 후 JSON 객체만 추출 (위치 무관)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            return jsonify({'ok': False, 'msg': 'AI가 JSON 형식으로 응답하지 않았습니다.', 'raw': raw[:300]})
        result = json.loads(json_match.group())
        return jsonify({'ok': True, 'result': result, 'analyzed_count': len(qnas)})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e), 'raw': raw[:300]})


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
