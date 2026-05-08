import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Memory Match Puzzle")

# Optional URLs for future deep linking in emails
APP_URL = os.getenv("APP_URL", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

def send_welcome_email(to_email: str, to_name: str) -> bool:
    print(f"[Mailer] Email send attempt to: {to_email}")
    print(f"[Mailer] SMTP host: {SMTP_HOST}")
    
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Mailer] Email failed: missing SMTP_USER or SMTP_PASSWORD in environment variables")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = "Welcome to Memory Match Puzzle!"
        
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
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        print("[Mailer] Email sent successfully")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[Mailer] Email failed: authentication error (check SMTP_PASSWORD, App Password required for Gmail)")
        return False
    except Exception as e:
        print(f"[Mailer] Email failed: connection timeout or other error -> {e}")
        return False

def send_leaderboard_alert_email(to_email: str, to_name: str, subject: str, message_body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Mailer] SMTP credentials missing. Cannot send leaderboard alert email.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = subject
        
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
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"[Mailer] Error sending leaderboard alert email: {e}")
        return False
