from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.services.mail_service import send_reset_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        remember = request.form.get('remember_me') == 'on'
        if user and user.check_password(password):
            if user.status == 'pending':
                flash('가입 승인 대기 중입니다. 관리자 승인 후 로그인할 수 있습니다.', 'error')
            elif user.status == 'inactive':
                flash('비활성화된 계정입니다. 관리자에게 문의해주세요.', 'error')
            else:
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        organization = request.form.get('organization', '').strip()
        job_title = request.form.get('job_title', '').strip()
        password = request.form.get('password', '')

        if not all([username, full_name, email, organization, job_title, password]):
            flash('모든 필수 항목을 입력해주세요.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('이미 사용 중인 아이디입니다.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('이미 사용 중인 이메일입니다.', 'error')
        else:
            user = User(username=username, email=email, organization=organization,
                        full_name=full_name, job_title=job_title)
            user.set_password(password)
            # 첫 번째 사용자는 admin + 자동 승인
            if User.query.count() == 0:
                user.role = 'admin'
                user.status = 'active'
            else:
                user.status = 'pending'
            db.session.add(user)
            db.session.commit()
            flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            email = request.form.get('email', '').strip()
            organization = request.form.get('organization', '').strip()
            full_name = request.form.get('full_name', '').strip()
            job_title = request.form.get('job_title', '').strip()

            if not all([email, full_name, organization, job_title]):
                flash('이름, 이메일, 조직명, 직책은 필수 항목입니다.', 'error')
            elif email != current_user.email and User.query.filter_by(email=email).first():
                flash('이미 사용 중인 이메일입니다.', 'error')
            else:
                current_user.email = email
                current_user.organization = organization
                current_user.full_name = full_name
                current_user.job_title = job_title
                db.session.commit()
                flash('정보가 수정되었습니다.', 'success')

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash('현재 비밀번호가 올바르지 않습니다.', 'error')
            elif len(new_pw) < 4:
                flash('새 비밀번호는 4자 이상이어야 합니다.', 'error')
            elif new_pw != confirm_pw:
                flash('새 비밀번호가 일치하지 않습니다.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('비밀번호가 변경되었습니다.', 'success')

        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        # 보안상 존재 여부 무관하게 동일 메시지
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            try:
                send_reset_email(user.email, user.username, reset_url)
                flash('비밀번호 재설정 링크를 이메일로 발송했습니다. 받은 편지함을 확인해주세요.', 'success')
            except Exception as e:
                flash(f'이메일 발송 실패: {str(e)}', 'error')
        else:
            flash('비밀번호 재설정 링크를 이메일로 발송했습니다. 받은 편지함을 확인해주세요.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.is_reset_token_valid(token):
        flash('유효하지 않거나 만료된 링크입니다. 다시 요청해주세요.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if len(new_pw) < 4:
            flash('비밀번호는 4자 이상이어야 합니다.', 'error')
        elif new_pw != confirm_pw:
            flash('비밀번호가 일치하지 않습니다.', 'error')
        else:
            user.set_password(new_pw)
            user.clear_reset_token()
            db.session.commit()
            flash('비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
