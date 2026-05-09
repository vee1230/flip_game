import os
import json
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Memory Match Puzzle")

def _send_via_brevo(to_email: str, to_name: str, subject: str, html_content: str) -> bool:
    print(f"[Mailer] Using Brevo API for: {to_email}")
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "sender": {"name": SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201, 202):
                print("[Mailer] Brevo API Email sent successfully")
                return True
            else:
                print(f"[Mailer] Brevo API returned status: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        print(f"[Mailer] Brevo API HTTPError: {e.code} - {error_msg}")
        return False
    except Exception as e:
        print(f"[Mailer] Brevo API Exception: {e}")
        return False


def _send_via_smtp(to_email: str, to_name: str, subject: str, html_content: str) -> bool:
    print(f"[Mailer] Using SMTP for: {to_email}")
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Mailer] Email failed: missing SMTP_USER or SMTP_PASSWORD in environment variables")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        print("[Mailer] SMTP Email sent successfully")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[Mailer] Email failed: authentication error (check SMTP_PASSWORD)")
        return False
    except Exception as e:
        print(f"[Mailer] Email failed: connection timeout or other error -> {e}")
        return False


def send_welcome_email(to_email: str, to_name: str) -> bool:
    subject = "Welcome to Memory Match Puzzle!"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <p>Hi {to_name},</p>
        <p>Welcome to Memory Match Puzzle!<br>
        Your account has been created successfully.</p>
        <p>You can now play games, save your progress, compete on the leaderboard, and unlock rewards.</p>
        <br>
        <p>Thank you,<br>
        {SMTP_FROM_NAME} Team</p>
    </body>
    </html>
    """
    
    if BREVO_API_KEY:
        return _send_via_brevo(to_email, to_name, subject, html)
    else:
        return _send_via_smtp(to_email, to_name, subject, html)


def send_leaderboard_alert_email(to_email: str, to_name: str, subject: str, message_body: str) -> bool:
    formatted_body = message_body.replace('\\n', '<br>').replace('\n', '<br>')
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; padding: 30px; color: #444; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <h2 style="color: #007bff; text-align: center; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid #f0f0f0; padding-bottom: 20px; font-size: 24px;">Leaderboard Update</h2>
        <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{to_name}</strong>,</p>
        <p style="font-size: 16px; line-height: 1.6;">{formatted_body}</p>
        <p style="font-size: 16px; line-height: 1.6; font-weight: bold; color: #333;">Play again now and reclaim your spot!</p>
        <br>
        <p style="font-size: 15px; color: #666; line-height: 1.5;">Best regards,<br><strong style="color: #222;">{SMTP_FROM_NAME} Team</strong></p>
    </div>
    """
    
    if BREVO_API_KEY:
        return _send_via_brevo(to_email, to_name, subject, html)
    else:
        return _send_via_smtp(to_email, to_name, subject, html)
