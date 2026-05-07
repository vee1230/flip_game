import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load .env from the project root (two levels up from utils: python_api/utils/..)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

def send_welcome_email(to_email: str, to_name: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        print("[Mailer] SMTP credentials missing. Cannot send welcome email.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Memory Match Puzzle Team <{SMTP_USER}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = "Welcome to Memory Match Puzzle"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; padding: 30px; color: #444; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="color: #28a745; text-align: center; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid #f0f0f0; padding-bottom: 20px; font-size: 24px;">Welcome to Memory Match!</h2>
            <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{to_name}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">Thank you for signing up using your Gmail account.</p>
            <p style="font-size: 16px; line-height: 1.6;">Your account has been successfully created. You can now enjoy the memory puzzle, save your scores, and compete with others.</p>
            <p style="font-size: 16px; line-height: 1.6;">We're excited to have you with us. Have fun and enjoy playing!</p>
            <br>
            <p style="font-size: 15px; color: #666; line-height: 1.5;">Best regards,<br><strong style="color: #222;">Memory Match Puzzle Team</strong></p>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"[Mailer] Error sending welcome email: {e}")
        return False

def send_leaderboard_alert_email(to_email: str, to_name: str, subject: str, message_body: str) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        print("[Mailer] SMTP credentials missing. Cannot send leaderboard alert email.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Memory Match Puzzle Team <{SMTP_USER}>"
        msg['To'] = f"{to_name} <{to_email}>"
        msg['Subject'] = subject
        
        # Replace newlines with <br> for HTML email
        formatted_body = message_body.replace('\\n', '<br>').replace('\n', '<br>')
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; padding: 30px; color: #444; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="color: #007bff; text-align: center; margin-top: 0; margin-bottom: 20px; border-bottom: 1px solid #f0f0f0; padding-bottom: 20px; font-size: 24px;">Leaderboard Update</h2>
            <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{to_name}</strong>,</p>
            <p style="font-size: 16px; line-height: 1.6;">{formatted_body}</p>
            <p style="font-size: 16px; line-height: 1.6; font-weight: bold; color: #333;">Play again now and reclaim your spot!</p>
            <br>
            <p style="font-size: 15px; color: #666; line-height: 1.5;">Best regards,<br><strong style="color: #222;">Memory Match Puzzle Team</strong></p>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"[Mailer] Error sending leaderboard alert email: {e}")
        return False
