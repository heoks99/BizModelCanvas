import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from flask import current_app


def send_reset_email(to_email, username, reset_url):
    mail_server   = current_app.config.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port     = int(current_app.config.get('MAIL_PORT') or os.environ.get('MAIL_PORT', 587))
    mail_username = current_app.config.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME', '')
    mail_password = current_app.config.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD', '')
    sender        = current_app.config.get('MAIL_DEFAULT_SENDER') or mail_username

    if not mail_username or not mail_password:
        raise RuntimeError('MAIL_USERNAME / MAIL_PASSWORD 환경변수가 설정되어 있지 않습니다.')

    html = f"""
    <div style="font-family:sans-serif; max-width:480px; margin:0 auto; padding:32px; background:#f8f9ff; border-radius:12px;">
        <h2 style="color:#1a1d27; margin-bottom:8px;">비밀번호 재설정</h2>
        <p style="color:#555e8a;">안녕하세요, <strong>{username}</strong>님.</p>
        <p style="color:#555e8a;">아래 버튼을 클릭하면 새 비밀번호를 설정할 수 있습니다.<br>링크는 <strong>1시간</strong> 동안 유효합니다.</p>
        <a href="{reset_url}"
           style="display:inline-block; margin:24px 0; padding:12px 28px;
                  background:#4f6ef7; color:#fff; border-radius:8px;
                  text-decoration:none; font-weight:600;">
            비밀번호 재설정하기
        </a>
        <p style="color:#8b92b8; font-size:12px;">
            본인이 요청하지 않은 경우 이 메일을 무시하세요.<br>
            링크: <a href="{reset_url}" style="color:#4f6ef7;">{reset_url}</a>
        </p>
        <hr style="border:none; border-top:1px solid #e0e4f0; margin:24px 0;">
        <p style="color:#8b92b8; font-size:11px;">사업전략관리포탈</p>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = '[사업전략관리포탈] 비밀번호 재설정 안내'
    msg['From'] = sender
    msg['To'] = to_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    with smtplib.SMTP(mail_server, mail_port) as server:
        server.ehlo()
        server.starttls()
        server.login(mail_username, mail_password)
        server.sendmail(sender, to_email, msg.as_string())
