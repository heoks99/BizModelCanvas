import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def send_reset_email(to_email, username, reset_url):
    cfg = current_app.config
    mail_user = cfg.get('MAIL_USERNAME', '')
    mail_pass = cfg.get('MAIL_PASSWORD', '')
    mail_sender = cfg.get('MAIL_DEFAULT_SENDER') or mail_user
    mail_server = cfg.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = cfg.get('MAIL_PORT', 587)
    mail_tls = cfg.get('MAIL_USE_TLS', True)

    if not mail_user or not mail_pass:
        raise RuntimeError('SMTP 설정이 되어 있지 않습니다. .env 파일에 MAIL_USERNAME과 MAIL_PASSWORD를 설정해주세요.')

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
        <p style="color:#8b92b8; font-size:11px;">사업모델캔버스</p>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = '[사업모델캔버스] 비밀번호 재설정 안내'
    msg['From'] = mail_sender
    msg['To'] = to_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    with smtplib.SMTP(mail_server, mail_port) as server:
        if mail_tls:
            server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(mail_sender, to_email, msg.as_string())
