import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.board import BoardPost, BoardComment, BoardReadStatus

board_bp = Blueprint('board', __name__, url_prefix='/board')

CATEGORIES = {'notice': '공지사항', 'manual': '매뉴얼'}


def _is_admin():
    return current_user.is_authenticated and current_user.role == 'admin'


VALID_SORTS = ('num', 'title', 'attach', 'author', 'date')


@board_bp.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'notice')
    sort = request.args.get('sort', 'date')
    sort_dir = request.args.get('dir', 'desc')

    if cat not in CATEGORIES:
        cat = 'notice'
    if sort not in VALID_SORTS:
        sort = 'date'
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    posts = BoardPost.query.filter_by(category=cat).all()

    def get_key(p):
        if sort == 'title':
            return p.title.lower()
        elif sort == 'author':
            return (p.owner.full_name or p.owner.username or '').lower()
        elif sort == 'attach':
            return (1 if p.file_name else 0, (p.file_name or '').lower())
        else:  # 'date' or 'num'
            return p.created_at

    rev = (sort_dir == 'desc')
    pinned = sorted([p for p in posts if p.is_pinned], key=get_key, reverse=rev)
    normal = sorted([p for p in posts if not p.is_pinned], key=get_key, reverse=rev)
    posts = pinned + normal

    # 읽은 게시글 ID 세트
    read_ids = set()
    if posts:
        post_ids = [p.id for p in posts]
        read_ids = {
            r.post_id for r in
            BoardReadStatus.query
            .filter_by(user_id=current_user.id)
            .filter(BoardReadStatus.post_id.in_(post_ids))
            .all()
        }

    counts = {c: BoardPost.query.filter_by(category=c).count() for c in CATEGORIES}

    # 순번: 생성일 오름차순 기준 고정 (최신 = 최대번호)
    normal_by_date = sorted([p for p in posts if not p.is_pinned], key=lambda p: p.created_at)
    total_normal = len(normal_by_date)
    post_nums = {p.id: total_normal - i for i, p in enumerate(normal_by_date)}

    return render_template('board/index.html',
                           posts=posts,
                           cat=cat,
                           categories=CATEGORIES,
                           counts=counts,
                           read_ids=read_ids,
                           sort=sort,
                           sort_dir=sort_dir,
                           post_nums=post_nums)


@board_bp.route('/<int:post_id>')
@login_required
def detail(post_id):
    post = BoardPost.query.get_or_404(post_id)
    post.view_count = (post.view_count or 0) + 1

    # 읽음 처리 (중복 무시)
    try:
        rs = BoardReadStatus()
        rs.user_id = current_user.id
        rs.post_id = post_id
        db.session.add(rs)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        db.session.commit()  # view_count 반영

    return render_template('board/detail.html', post=post, categories=CATEGORIES)


@board_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if not _is_admin():
        flash('관리자만 게시글을 작성할 수 있습니다.', 'error')
        return redirect(url_for('board.index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        cat = request.form.get('category', 'notice')
        is_pinned = bool(request.form.get('is_pinned'))

        if not title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('board/form.html', post=None, categories=CATEGORIES)
        if cat not in CATEGORIES:
            cat = 'notice'

        post = BoardPost()
        post.title = title
        post.content = content
        post.category = cat
        post.is_pinned = is_pinned
        post.owner_id = current_user.id

        f = request.files.get('file')
        if f and f.filename:
            post.file_name = f.filename
            post.file_data = f.read()
            post.file_mime = f.mimetype or 'application/octet-stream'

        db.session.add(post)
        db.session.commit()
        flash('게시글이 등록되었습니다.', 'success')
        return redirect(url_for('board.detail', post_id=post.id))

    return render_template('board/form.html', post=None, categories=CATEGORIES)


@board_bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if not _is_admin():
        flash('관리자만 게시글을 수정할 수 있습니다.', 'error')
        return redirect(url_for('board.index'))

    post = BoardPost.query.get_or_404(post_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        cat = request.form.get('category', 'notice')
        is_pinned = bool(request.form.get('is_pinned'))

        if not title:
            flash('제목을 입력해주세요.', 'error')
            return render_template('board/form.html', post=post, categories=CATEGORIES)

        post.title = title
        post.content = content
        post.category = cat if cat in CATEGORIES else 'notice'
        post.is_pinned = is_pinned

        f = request.files.get('file')
        if f and f.filename:
            post.file_name = f.filename
            post.file_data = f.read()
            post.file_mime = f.mimetype or 'application/octet-stream'

        if request.form.get('delete_file') and post.file_name:
            post.file_name = None
            post.file_data = None
            post.file_mime = None

        db.session.commit()
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('board.detail', post_id=post.id))

    return render_template('board/form.html', post=post, categories=CATEGORIES)


@board_bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    if not _is_admin():
        flash('관리자만 게시글을 삭제할 수 있습니다.', 'error')
        return redirect(url_for('board.index'))

    post = BoardPost.query.get_or_404(post_id)
    cat = post.category
    db.session.delete(post)
    db.session.commit()
    flash('게시글이 삭제되었습니다.', 'success')
    return redirect(url_for('board.index', cat=cat))


@board_bp.route('/<int:post_id>/download')
@login_required
def download_file(post_id):
    post = BoardPost.query.get_or_404(post_id)
    if not post.file_data:
        flash('첨부 파일이 없습니다.', 'error')
        return redirect(url_for('board.detail', post_id=post_id))
    return send_file(
        io.BytesIO(post.file_data),
        mimetype=post.file_mime or 'application/octet-stream',
        as_attachment=True,
        download_name=post.file_name or 'download'
    )


# ── 댓글 ──────────────────────────────────────────────────────

@board_bp.route('/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    BoardPost.query.get_or_404(post_id)  # 게시글 존재 확인
    content = request.form.get('content', '').strip()
    if not content:
        flash('댓글 내용을 입력해주세요.', 'error')
        return redirect(url_for('board.detail', post_id=post_id) + '#comments')

    comment = BoardComment()
    comment.post_id = post_id
    comment.owner_id = current_user.id
    comment.content = content
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('board.detail', post_id=post_id) + '#comments')


@board_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = BoardComment.query.get_or_404(comment_id)
    post_id = comment.post_id

    if comment.owner_id != current_user.id and not _is_admin():
        flash('댓글을 삭제할 권한이 없습니다.', 'error')
        return redirect(url_for('board.detail', post_id=post_id) + '#comments')

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('board.detail', post_id=post_id) + '#comments')
