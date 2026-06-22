import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from backend.config import settings


def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """Send an email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    reset_url = f"http://localhost:8000/reset-password?token={reset_token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#6B3F1A">Monika G Cafe</h2>
      <p>You requested a password reset. Click the button below:</p>
      <a href="{reset_url}" style="display:inline-block;padding:12px 28px;
         background:#C17B3F;color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">
        Reset Password
      </a>
      <p style="color:#888;font-size:12px">This link expires in 1 hour.
         If you did not request this, ignore this email.</p>
    </div>
    """
    return send_email(to_email, "Reset your Monika G Cafe password", html)


def send_order_confirmation_email(to_email: str, order_number: str, total: float) -> bool:
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px">
      <h2 style="color:#6B3F1A">Order Confirmed ✓</h2>
      <p>Thank you! Your order <strong>{order_number}</strong> has been received.</p>
      <p>Total: <strong>₹{total:.2f}</strong></p>
      <p>We'll notify you when it's ready. Enjoy your experience at Monika G Cafe!</p>
    </div>
    """
    return send_email(to_email, f"Order {order_number} Confirmed", html)


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via Twilio."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"Your Monika G Cafe OTP is: {otp}. Valid for 10 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone,
        )
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=10)