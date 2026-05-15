import os
from flask import current_app


def send_reset_email(to_email, username, reset_url):
    api_key = current_app.config.get('SENDGRID_API_KEY') or os.environ.get('SENDGRID_API_KEY', '')
    sender  = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME', '')

    if not api_key:
        raise RuntimeError('SENDGRID_API_KEY 환경변수가 설정되어 있지 않습니다. Railway Variables를 확인해주세요.')
    if not sender:
        raise RuntimeError('MAIL_DEFAULT_SENDER 환경변수가 설정되어 있지 않습니다.')

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

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=sender,
        to_emails=to_email,
        subject='[사업전략관리포탈] 비밀번호 재설정 안내',
        html_content=html,
    )
    sg = SendGridAPIClient(api_key)
    response = sg.send(message)

    if response.status_code not in (200, 202):
        raise RuntimeError(f'SendGrid 발송 실패: status={response.status_code} body={response.body}')
