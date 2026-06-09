import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user

from app import db
from app.models.board import BoardPost

board_bp = Blueprint('board', __name__, url_prefix='/board')

CATEGORIES = {'notice': '공지사항', 'manual': '매뉴얼'}


def _is_admin():
    return current_user.is_authenticated and current_user.role == 'admin'


@board_bp.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'notice')
    if cat not in CATEGORIES:
        cat = 'notice'

    posts = (BoardPost.query
             .filter_by(category=cat)
             .order_by(BoardPost.is_pinned.desc(), BoardPost.created_at.desc())
             .all())

    counts = {c: BoardPost.query.filter_by(category=c).count() for c in CATEGORIES}
    return render_template('board/index.html', posts=posts, cat=cat,
                           categories=CATEGORIES, counts=counts)


@board_bp.route('/<int:post_id>')
@login_required
def detail(post_id):
    post = BoardPost.query.get_or_404(post_id)
    post.view_count = (post.view_count or 0) + 1
    db.session.commit()
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

        # 파일 삭제 요청
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
