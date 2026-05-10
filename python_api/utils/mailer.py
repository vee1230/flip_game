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
    import datetime
    import uuid
    print(f"[Mailer] Using SMTP for: {to_email}")
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Mailer] Email failed: missing SMTP_USER or SMTP_PASSWORD in environment variables")
        return False
        
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = subject
        msg['Message-ID'] = f"<{uuid.uuid4()}@memorymatchpuzzle.app>"
        msg['Date'] = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        msg['X-Mailer'] = 'Memory Match Puzzle Mailer'
        msg['Precedence'] = 'bulk'
        msg['List-Unsubscribe'] = '<https://flip-game-live.vercel.app/>'
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
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
    subject = "Welcome to Memory Match Puzzle! Your account is ready"
    html = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#0a0a1a; font-family:'Segoe UI',Arial,sans-serif;">
      <div style="max-width:600px; margin:0 auto; background:linear-gradient(135deg,#0f0c29 0%,#1a1a3e 50%,#24243e 100%); border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,0.08);">
        
        <!-- Header Banner -->
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); padding:40px 30px; text-align:center;">
          <div style="font-size:48px; margin-bottom:8px;">🧩</div>
          <h1 style="margin:0; color:#ffffff; font-size:28px; font-weight:700; letter-spacing:-0.5px;">Memory Match Puzzle</h1>
          <p style="margin:8px 0 0; color:rgba(255,255,255,0.85); font-size:14px;">Train your brain. Challenge your friends.</p>
        </div>

        <!-- Welcome Message -->
        <div style="padding:32px 30px 24px;">
          <h2 style="margin:0 0 8px; color:#e0e0ff; font-size:22px;">Welcome aboard, {to_name}! 🎉</h2>
          <p style="margin:0 0 20px; color:rgba(255,255,255,0.65); font-size:15px; line-height:1.6;">
            Your account has been created successfully. You're now part of a growing community of memory champions!
          </p>

          <!-- Play Now Button -->
          <div style="text-align:center; margin:28px 0;">
            <a href="https://flip-game-live.vercel.app/" 
               style="display:inline-block; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:#ffffff; text-decoration:none; padding:16px 48px; border-radius:50px; font-size:18px; font-weight:700; letter-spacing:0.5px;">
              ▶ PLAY NOW
            </a>
          </div>
        </div>

        <!-- Feature Cards -->
        <div style="padding:0 30px 28px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate; border-spacing:0 10px;">
            <tr>
              <td style="background:rgba(102,126,234,0.12); border-radius:12px; padding:16px 18px; border:1px solid rgba(102,126,234,0.2);">
                <span style="font-size:20px;">🏆</span>
                <span style="color:#e0e0ff; font-size:14px; font-weight:600; margin-left:10px;">Leaderboard</span>
                <p style="margin:6px 0 0; color:rgba(255,255,255,0.5); font-size:12px;">Compete with players worldwide</p>
              </td>
            </tr>
            <tr>
              <td style="background:rgba(118,75,162,0.12); border-radius:12px; padding:16px 18px; border:1px solid rgba(118,75,162,0.2);">
                <span style="font-size:20px;">⭐</span>
                <span style="color:#e0e0ff; font-size:14px; font-weight:600; margin-left:10px;">Daily Rewards</span>
                <p style="margin:6px 0 0; color:rgba(255,255,255,0.5); font-size:12px;">Earn stars and unlock achievements</p>
              </td>
            </tr>
            <tr>
              <td style="background:rgba(102,126,234,0.12); border-radius:12px; padding:16px 18px; border:1px solid rgba(102,126,234,0.2);">
                <span style="font-size:20px;">🎯</span>
                <span style="color:#e0e0ff; font-size:14px; font-weight:600; margin-left:10px;">Multiple Themes</span>
                <p style="margin:6px 0 0; color:rgba(255,255,255,0.5); font-size:12px;">Animals, Food, Space, Nature &amp; more</p>
              </td>
            </tr>
            <tr>
              <td style="background:rgba(118,75,162,0.12); border-radius:12px; padding:16px 18px; border:1px solid rgba(118,75,162,0.2);">
                <span style="font-size:20px;">🤝</span>
                <span style="color:#e0e0ff; font-size:14px; font-weight:600; margin-left:10px;">Multiplayer</span>
                <p style="margin:6px 0 0; color:rgba(255,255,255,0.5); font-size:12px;">Challenge friends in real-time matches</p>
              </td>
            </tr>
          </table>
        </div>

        <!-- Footer -->
        <div style="padding:20px 30px; border-top:1px solid rgba(255,255,255,0.06); text-align:center;">
          <p style="margin:0; color:rgba(255,255,255,0.35); font-size:12px;">
            © 2026 {SMTP_FROM_NAME} · All rights reserved
          </p>
          <p style="margin:6px 0 0;">
            <a href="https://flip-game-live.vercel.app/" style="color:rgba(102,126,234,0.7); font-size:12px; text-decoration:none;">Visit Game</a>
          </p>
        </div>

      </div>
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
