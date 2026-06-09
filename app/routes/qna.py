import re
import threading
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.qna import QnA, QnAComment
from app.models.project import Project

qna_bp = Blueprint('qna', __name__, url_prefix='/qna')


# ── AI 답변 생성 ──────────────────────────────────────────────
def _call_claude(system, user_msg, app):
    """Claude API 호출. app context 안에서 실행해야 함."""
    import anthropic
    client = anthropic.Anthropic(api_key=app.config.get('ANTHROPIC_API_KEY', ''))
    message = client.messages.create(
        model='claude-opus-4-8',
        max_tokens=4000,
        thinking={'type': 'adaptive'},
        system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': user_msg}]
    )
    result = next(b.text for b in message.content if b.type == 'text').strip()
    result = re.sub(r'^```[a-z]*\n?', '', result)
    result = re.sub(r'\n?```$', '', result)
    return result


def _build_system():
    from app.services.ai_service import BMC_SYSTEM
    HTML_GUIDE = """
사용자의 전략 질문에 대해 BCG 수석 컨설턴트로서 전문적으로 답변하세요.
답변은 순수 HTML로만 작성하세요. 아래 구조와 CSS 클래스를 반드시 사용하세요.

## 출력 구조 (순서 필수)
1. 핵심 요약 박스 → 2. 본론 섹션(h3) → 3. 강조/인사이트 → 4. 결론·액션

## HTML 클래스 사용 규칙

### [필수] 핵심 요약 — 답변 맨 앞에 항상 삽입
<div class="bcg-summary-box">
  <div class="bcg-summary-box-title">핵심 요약</div>
  <p>질문의 핵심 답변을 2~3문장으로. <strong>중요 키워드</strong>는 strong 태그.</p>
</div>

### 섹션 구분
<h3>섹션 제목</h3>   — 주요 섹션 (자동 스타일: navy + teal 밑선)
<h4>소항목 제목</h4> — 하위 항목

### 본문 강조
<strong>핵심 단어</strong>   — 중요 키워드·수치
<div class="bcg-insight"><strong>포인트명:</strong> 설명 내용</div>   — 파랑 인사이트 박스
<div class="bcg-insight-warn"><strong>주의:</strong> 경고 내용</div>  — 노랑 경고 박스
<div class="bcg-callout">최우선 핵심 메시지 한 줄</div>             — 초록 핵심 callout

### 리스트
<ul><li>항목</li></ul>   — 일반 불릿
<div class="bcg-implication">▸ 시사점 내용</div>   — 전략적 시사점

### 액션 스텝 (순서 있는 행동방안)
<div class="bcg-step-list">
  <div class="bcg-step"><div class="bcg-step-num">1</div><div><strong>단계명:</strong> 설명</div></div>
  <div class="bcg-step"><div class="bcg-step-num">2</div><div><strong>단계명:</strong> 설명</div></div>
</div>

### 표 (비교·정리)
<table class="bcg-table">
  <thead><tr><th>항목</th><th>내용</th></tr></thead>
  <tbody><tr><td>값1</td><td>값2</td></tr></tbody>
</table>

### 핵심 지표 (숫자·수치가 있을 때)
<div class="bcg-metric-row">
  <div class="bcg-metric-item"><div class="bcg-metric-val">수치</div><div class="bcg-metric-label">라벨</div></div>
</div>

### 2열 비교
<div class="bcg-two-col">
  <div><strong>항목 A</strong><p>설명</p></div>
  <div><strong>항목 B</strong><p>설명</p></div>
</div>

### 우선순위·배지
<span class="bcg-badge-high">높음</span>  <span class="bcg-badge-mid">중간</span>  <span class="bcg-badge-low">낮음</span>
<span class="bcg-priority-1">최우선 항목</span>

## 지침
- 반드시 bcg-summary-box로 시작
- 각 주요 섹션은 <h3>으로 구분, 소항목은 <h4>
- 수치·핵심어는 항상 <strong>
- 행동방안은 bcg-step-list로 번호 표시
- 비교는 bcg-table 또는 bcg-two-col
- markdown(#, **, -) 사용 절대 금지, 순수 HTML만
"""
    return BMC_SYSTEM + "\n" + HTML_GUIDE


def _build_project_context(project):
    if not project:
        return ''
    ctx = f'프로젝트명: {project.name}'
    if project.organization:
        ctx += f'\n수행 조직: {project.organization}'
    if project.description:
        ctx += f'\n설명: {project.description}'
    return ctx


def _build_thread_context(qna):
    lines = [f'[원본 질문]\n{qna.content}']
    if qna.ai_answer:
        plain = re.sub(r'<[^>]+>', '', qna.ai_answer)[:500]
        lines.append(f'[AI 첫 번째 답변 요약]\n{plain.strip()}')
    for c in qna.comments:
        lines.append(f'[답글]\n{c.content}')
        if c.ai_answer:
            plain = re.sub(r'<[^>]+>', '', c.ai_answer)[:300]
            lines.append(f'[AI 답변 요약]\n{plain.strip()}')
    return '\n\n'.join(lines)


def _async_answer_qna(app, qna_id, project_context):
    """백그라운드 스레드에서 QnA 본문 AI 답변 생성"""
    with app.app_context():
        qna = QnA.query.get(qna_id)
        if not qna:
            return
        try:
            system = _build_system()
            user_msg = f"[질문 제목]\n{qna.title}\n\n[질문 내용]\n{qna.content}"
            if project_context:
                user_msg += f"\n\n[관련 프로젝트 정보]\n{project_context}"
            qna.ai_answer = _call_claude(system, user_msg, app)
        except Exception as e:
            qna.ai_answer = f'<div class="bcg-insight-warn"><strong>AI 답변 오류:</strong> {str(e)}</div>'
        finally:
            qna.ai_pending = False
            db.session.commit()


def _async_answer_comment(app, comment_id, qna_id, project_context):
    """백그라운드 스레드에서 댓글 AI 답변 생성"""
    with app.app_context():
        comment = QnAComment.query.get(comment_id)
        qna = QnA.query.get(qna_id)
        if not comment or not qna:
            return
        try:
            system = _build_system()
            thread_context = _build_thread_context(qna)
            user_msg = f"[질문 제목]\n{qna.title}\n\n[답글 내용]\n{comment.content}"
            if project_context:
                user_msg += f"\n\n[관련 프로젝트 정보]\n{project_context}"
            if thread_context:
                user_msg += f"\n\n[이전 대화 맥락]\n{thread_context}"
            comment.ai_answer = _call_claude(system, user_msg, app)
        except Exception as e:
            comment.ai_answer = f'<div class="bcg-insight-warn"><strong>AI 답변 오류:</strong> {str(e)}</div>'
        finally:
            comment.ai_pending = False
            db.session.commit()


# ── 라우트 ────────────────────────────────────────────────────
@qna_bp.route('/')
@login_required
def index():
    is_admin = current_user.role == 'admin'
    qnas = QnA.query.order_by(QnA.created_at.desc()).all()
    return render_template('qna/index.html', qnas=qnas, is_admin=is_admin)


@qna_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.name).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        project_id = request.form.get('project_id') or None
        want_ai = request.form.get('want_ai') == '1'

        if not title or not content:
            flash('제목과 내용을 입력해주세요.', 'error')
            return render_template('qna/new.html', projects=projects)

        project = None
        if project_id:
            project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first()

        qna = QnA(
            owner_id=current_user.id,
            title=title,
            content=content,
            project_id=project.id if project else None,
            ai_pending=want_ai,
        )
        db.session.add(qna)
        db.session.commit()

        if want_ai:
            app = current_app._get_current_object()
            project_context = _build_project_context(project)
            t = threading.Thread(target=_async_answer_qna, args=(app, qna.id, project_context))
            t.daemon = True
            t.start()

        flash('질문이 등록되었습니다.', 'success')
        return redirect(url_for('qna.detail', qna_id=qna.id))

    return render_template('qna/new.html', projects=projects)


@qna_bp.route('/<int:qna_id>')
@login_required
def detail(qna_id):
    qna = QnA.query.filter_by(id=qna_id).first_or_404()
    is_owner = qna.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    return render_template('qna/detail.html', qna=qna, is_owner=is_owner, is_admin=is_admin)


# ── AI 상태 폴링 ──────────────────────────────────────────────
@qna_bp.route('/<int:qna_id>/status')
@login_required
def status(qna_id):
    qna = QnA.query.filter_by(id=qna_id).first_or_404()
    return jsonify({
        'pending': qna.ai_pending,
        'answer': qna.ai_answer,
    })


@qna_bp.route('/<int:qna_id>/comment/<int:comment_id>/status')
@login_required
def comment_status(qna_id, comment_id):
    QnA.query.filter_by(id=qna_id).first_or_404()
    comment = QnAComment.query.filter_by(id=comment_id, qna_id=qna_id).first_or_404()
    return jsonify({
        'pending': comment.ai_pending,
        'answer': comment.ai_answer,
    })


# ── AI 답변 요청 ──────────────────────────────────────────────
@qna_bp.route('/<int:qna_id>/request_ai', methods=['POST'])
@login_required
def request_ai(qna_id):
    qna = QnA.query.filter_by(id=qna_id).first_or_404()
    is_owner = qna.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    if not is_owner and not is_admin:
        return jsonify({'ok': False, 'msg': '권한이 없습니다.'})
    if qna.ai_pending:
        return jsonify({'ok': False, 'msg': '이미 생성 중입니다.'})
    qna.ai_pending = True
    qna.ai_answer = None
    db.session.commit()

    app = current_app._get_current_object()
    project_context = _build_project_context(qna.project)
    t = threading.Thread(target=_async_answer_qna, args=(app, qna.id, project_context))
    t.daemon = True
    t.start()
    return jsonify({'ok': True})


@qna_bp.route('/<int:qna_id>/comment/<int:comment_id>/request_ai', methods=['POST'])
@login_required
def request_comment_ai(qna_id, comment_id):
    QnA.query.filter_by(id=qna_id).first_or_404()
    comment = QnAComment.query.filter_by(id=comment_id, qna_id=qna_id).first_or_404()
    is_comment_owner = comment.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    if not is_comment_owner and not is_admin:
        return jsonify({'ok': False, 'msg': '권한이 없습니다.'})
    if comment.ai_pending:
        return jsonify({'ok': False, 'msg': '이미 생성 중입니다.'})
    comment.ai_pending = True
    comment.ai_answer = None
    db.session.commit()

    app = current_app._get_current_object()
    qna = QnA.query.get(qna_id)
    project_context = _build_project_context(qna.project if qna else None)
    t = threading.Thread(target=_async_answer_comment, args=(app, comment.id, qna_id, project_context))
    t.daemon = True
    t.start()
    return jsonify({'ok': True})


# ── 답글(댓글) ────────────────────────────────────────────────
@qna_bp.route('/<int:qna_id>/comment', methods=['POST'])
@login_required
def add_comment(qna_id):
    qna = QnA.query.filter_by(id=qna_id).first_or_404()
    is_owner = qna.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    if not is_owner and not is_admin:
        flash('답글 작성 권한이 없습니다.', 'error')
        return redirect(url_for('qna.detail', qna_id=qna_id))

    content = request.form.get('content', '').strip()
    want_ai = request.form.get('want_ai') == '1'

    if not content:
        flash('답글 내용을 입력해주세요.', 'error')
        return redirect(url_for('qna.detail', qna_id=qna_id))

    comment = QnAComment(
        qna_id=qna_id,
        owner_id=current_user.id,
        content=content,
        ai_pending=want_ai,
    )
    db.session.add(comment)
    db.session.commit()

    if want_ai:
        app = current_app._get_current_object()
        project_context = _build_project_context(qna.project)
        t = threading.Thread(target=_async_answer_comment,
                             args=(app, comment.id, qna_id, project_context))
        t.daemon = True
        t.start()

    return redirect(url_for('qna.detail', qna_id=qna_id) + '#entry-comment-' + str(comment.id))


@qna_bp.route('/<int:qna_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(qna_id, comment_id):
    QnA.query.filter_by(id=qna_id).first_or_404()
    comment = QnAComment.query.filter_by(id=comment_id, qna_id=qna_id).first_or_404()
    is_comment_owner = comment.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    if not is_comment_owner and not is_admin:
        flash('삭제 권한이 없습니다.', 'error')
        return redirect(url_for('qna.detail', qna_id=qna_id))
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('qna.detail', qna_id=qna_id))


@qna_bp.route('/<int:qna_id>/delete', methods=['POST'])
@login_required
def delete(qna_id):
    qna = QnA.query.filter_by(id=qna_id).first_or_404()
    is_owner = qna.owner_id == current_user.id
    is_admin = current_user.role == 'admin'
    if not is_owner and not is_admin:
        flash('삭제 권한이 없습니다.', 'error')
        return redirect(url_for('qna.detail', qna_id=qna_id))
    db.session.delete(qna)
    db.session.commit()
    flash('질문이 삭제되었습니다.', 'success')
    return redirect(url_for('qna.index'))
