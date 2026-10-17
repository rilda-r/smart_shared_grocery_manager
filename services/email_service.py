"""
services/email_service.py
=========================
Production-ready transactional email service for GrocEase.
Supports live SMTP delivery (Brevo, Resend, SendGrid, Gmail App Password, AWS SES, etc.)
with automated fallback logging in development mode.
"""

import os
import smtplib
import threading
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger("grocease.email")


def _get_smtp_config() -> dict:
    """Retrieve and sanitize SMTP settings from environment."""
    host = (os.environ.get("SMTP_HOST") or os.environ.get("GROCEASE_SMTP_HOST", "")).strip()
    port_str = os.environ.get("SMTP_PORT") or os.environ.get("GROCEASE_SMTP_PORT", "587")
    try:
        port = int(port_str)
    except ValueError:
        port = 587

    user = (os.environ.get("SMTP_USER") or os.environ.get("GROCEASE_SMTP_USER", "")).strip()
    password = (os.environ.get("SMTP_PASSWORD") or os.environ.get("GROCEASE_SMTP_PASSWORD", "")).strip()
    sender = (
        os.environ.get("SMTP_SENDER_EMAIL")
        or os.environ.get("GROCEASE_SMTP_SENDER_EMAIL")
        or os.environ.get("SMTP_FROM")
        or user
        or "noreply@grocease.app"
    ).strip()

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender,
    }


def smtp_is_configured() -> bool:
    """
    Returns True only if live SMTP credentials are real and not placeholder defaults.
    """
    dev_mode = os.environ.get("GROCEASE_DEV_MODE", "false").lower() in ("true", "1", "yes", "on")
    if dev_mode:
        return False

    cfg = _get_smtp_config()
    host = cfg["host"].lower()
    user = cfg["user"].lower()
    password = cfg["password"].lower()

    if not host or "example.com" in host or "your-smtp" in host:
        return False
    if not user or "your-smtp" in user:
        return False
    if not password or "your-smtp" in password:
        return False

    return True


def _send_raw_smtp(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
    """Synchronous internal worker that performs SMTP socket connection and message transmission."""
    cfg = _get_smtp_config()

    if not smtp_is_configured():
        # Clean local developer simulation output (safe for Windows cp1252 consoles)
        try:
            print(f"\n[LOCAL DEV MAIL SIMULATION]")
            print(f"   To: {to_email}")
            print(f"   Subject: {subject}")
            if text_content:
                first_lines = text_content.strip().splitlines()[:3]
                print(f"   Snippet: {' '.join(first_lines)}")
            print(f"   (Configure real SMTP keys in .env to deliver to real inboxes)\n")
        except Exception:
            pass
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"GrocEase <{cfg['sender']}>"
        msg["To"] = to_email

        # Attach plain text version
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))

        # Attach HTML version
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Connect according to port (SSL vs STARTTLS)
        if cfg["port"] == 465:
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=12)
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=12)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["sender"], [to_email], msg.as_string())
        server.quit()
        print(f"[SMTP SUCCESS] Successfully delivered '{subject}' to {to_email}")
        return True
    except Exception as exc:
        print(f"[SMTP ERROR] Failed sending email to {to_email} via {cfg['host']}:{cfg['port']} -> {exc}")
        return False


def send_email_async(to_email: str, subject: str, html_content: str, text_content: str = ""):
    """Dispatches email asynchronously in a background daemon thread to avoid blocking UI or DB transactions."""
    thread = threading.Thread(
        target=_send_raw_smtp,
        args=(to_email, subject, html_content, text_content),
        daemon=True,
    )
    thread.start()


# ==============================================================================
# GrocEase Warm Aesthetic HTML Email Templates
# ==============================================================================

def _wrap_email_html(headline: str, body_html: str, action_box_html: str = "") -> str:
    """Wraps body content in the signature GrocEase 'Shared Kitchen Counter' styling."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 0; background-color: #F3EBDD; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #2A1D16; }}
  .container {{ max-width: 580px; margin: 30px auto; background-color: #FBF6EC; border: 1px solid #E3D6BE; border-top: 5px solid #7A1F2B; border-radius: 16px; overflow: hidden; box-shadow: 0 6px 24px rgba(59, 42, 32, 0.08); }}
  .header {{ padding: 28px 32px 18px 32px; text-align: center; border-bottom: 1px solid #E3D6BE; background: #FAF3E6; }}
  .brand {{ font-size: 26px; font-weight: 800; color: #7A1F2B; text-decoration: none; letter-spacing: -0.5px; }}
  .tagline {{ font-size: 13px; color: #5C4A3E; margin-top: 4px; }}
  .content {{ padding: 32px; font-size: 15px; line-height: 1.6; color: #2A1D16; }}
  .headline {{ font-size: 22px; font-weight: 700; color: #7A1F2B; margin-top: 0; margin-bottom: 16px; }}
  .action-box {{ background: #F7F2E8; border: 1.5px dashed #E3D6BE; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0; }}
  .footer {{ padding: 20px 32px; background: #EADFCB; text-align: center; font-size: 12px; color: #5C4A3E; border-top: 1px solid #E3D6BE; }}
</style>
</head>
<body>
<div style="background-color: #F3EBDD; padding: 20px 10px;">
  <div class="container">
    <div class="header">
      <div class="brand">🛒 GrocEase</div>
      <div class="tagline">Shop together. Split smarter.</div>
    </div>
    <div class="content">
      <h2 class="headline">{headline}</h2>
      {body_html}
      {action_box_html}
    </div>
    <div class="footer">
      <p style="margin: 0 0 6px 0;">This email was sent by GrocEase — Shared Grocery & Expense Management.</p>
      <p style="margin: 0;">© 2026 GrocEase. All rights reserved.</p>
    </div>
  </div>
</div>
</body>
</html>"""


# ==============================================================================
# Transactional Email Functions
# ==============================================================================

def send_otp_email(email: str, otp: str, purpose: str = "verification"):
    """
    Sends the 6-digit OTP code for email verification or password reset.
    """
    clean_email = email.strip()
    is_reset = purpose.lower() == "password_reset"
    subject = "Reset your GrocEase password" if is_reset else "Your GrocEase verification code"

    action_title = "Password Reset Code" if is_reset else "Email Verification Code"
    instruction = (
        "We received a request to reset your GrocEase account password."
        if is_reset
        else "Thank you for joining GrocEase! Please enter this 6-digit verification code to activate your account."
    )

    body_html = f"""
    <p>Hi there,</p>
    <p>{instruction}</p>
    <p>This verification code is strictly valid for <strong>10 minutes</strong>. Never share this code with anyone.</p>
    """

    action_box = f"""
    <div class="action-box">
      <div style="font-size: 13px; font-weight: 700; color: #5C4A3E; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{action_title}</div>
      <div style="font-size: 36px; font-weight: 800; letter-spacing: 6px; color: #7A1F2B; font-family: monospace;">{otp}</div>
    </div>
    """

    text_content = f"""GrocEase — {action_title}

{instruction}

Your 6-digit code is: {otp}
(Valid for 10 minutes)

If you did not request this, please safely disregard this email.
"""

    html_content = _wrap_email_html(action_title, body_html, action_box)
    send_email_async(clean_email, subject, html_content, text_content)


def send_welcome_email(email: str, full_name: str = "Friend"):
    """
    Post-Registration Trigger: Dispatches an onboarding welcome email immediately
    after user creates and verifies their account.
    """
    clean_email = email.strip()
    display_name = full_name.strip() if full_name else "Friend"
    subject = f"🎉 Welcome to GrocEase, {display_name}!"

    body_html = f"""
    <p>Hi <strong>{display_name}</strong>,</p>
    <p>Welcome to <strong>GrocEase</strong> — your shared kitchen counter is now officially open! We are thrilled to help you and your roommates shop together and split expenses effortlessly.</p>
    
    <div style="margin: 20px 0; padding: 16px 20px; background: #FFFDF9; border-left: 4px solid #6B8F71; border-radius: 8px;">
      <h3 style="margin: 0 0 8px 0; color: #2E5135; font-size: 16px;">Quick Ways to Get Started:</h3>
      <ul style="margin: 0; padding-left: 20px; color: #3B2A20; font-size: 14px; line-height: 1.8;">
        <li><strong>🏠 Create or Join a Room:</strong> Generate a unique 8-character invite code and invite your flatmates.</li>
        <li><strong>🧺 Shared Grocery List:</strong> Add items you need; roommates see updates in real time.</li>
        <li><strong>📷 Instant Bill Scanning:</strong> Snap a photo of your receipt to auto-extract items and map costs.</li>
        <li><strong>💳 Transparent Debt Tracking:</strong> Settle up with 1-click payment confirmations.</li>
      </ul>
    </div>
    
    <p>If you have any questions or feedback, we are always here to help.</p>
    <p style="margin-top: 24px;">Happy shopping,<br><strong>The GrocEase Team</strong></p>
    """

    action_box = """
    <div class="action-box">
      <div style="font-weight: 700; color: #7A1F2B; font-size: 16px; margin-bottom: 6px;">Your Account is Fully Verified & Active</div>
      <div style="font-size: 13px; color: #5C4A3E;">You can now log in anytime and start collaborating.</div>
    </div>
    """

    text_content = f"""Welcome to GrocEase, {display_name}!

Your account has been successfully verified and activated.

Here is what you can do next:
1. Create or join a shared flat/house room with an 8-character code.
2. Add grocery items with real-time sync for all roommates.
3. Upload grocery receipts for automated OCR expense splitting.
4. Keep personal budgets and track who owes what seamlessly.

Happy shopping!
The GrocEase Team
"""

    html_content = _wrap_email_html("Welcome to GrocEase!", body_html, action_box)
    send_email_async(clean_email, subject, html_content, text_content)


def send_account_deleted_email(email: str, full_name: str = "Valued User"):
    """
    Account Deletion Trigger: Event hook that captures when a user account or profile
    is permanently deleted. Dispatches formal confirmation immediately prior to deletion.
    """
    clean_email = email.strip()
    display_name = full_name.strip() if full_name else "Valued User"
    subject = "Your GrocEase account has been successfully deleted"

    body_html = f"""
    <p>Dear <strong>{display_name}</strong>,</p>
    <p>This is formal confirmation that your GrocEase user account (<strong>{clean_email}</strong>) and all associated personal data have been permanently deleted from our records.</p>
    
    <div style="margin: 20px 0; padding: 16px 20px; background: #FCEAE8; border-left: 4px solid #8C1C13; border-radius: 8px;">
      <h3 style="margin: 0 0 6px 0; color: #8C1C13; font-size: 15px;">Summary of Deletion:</h3>
      <p style="margin: 0; color: #5C4A3E; font-size: 13px; line-height: 1.6;">
        All your profile details, room memberships, personal expense tracking, and authentication credentials have been completely removed.
      </p>
    </div>
    
    <p>Thank you for having been part of GrocEase. If you ever wish to return in the future, you are always welcome to register a new account.</p>
    <p style="margin-top: 24px;">Warm regards,<br><strong>The GrocEase Team</strong></p>
    """

    action_box = """
    <div class="action-box">
      <div style="font-weight: 700; color: #8C1C13; font-size: 15px; margin-bottom: 4px;">Account Deletion Complete</div>
      <div style="font-size: 12px; color: #5C4A3E;">If you did not authorize this action, please contact support immediately.</div>
    </div>
    """

    text_content = f"""Dear {display_name},

This email formally confirms that your GrocEase account ({clean_email}) has been permanently deleted.

All your user profile records, room memberships, and personal data have been removed.

Thank you for using GrocEase.
The GrocEase Team
"""

    html_content = _wrap_email_html("Account Successfully Deleted", body_html, action_box)
    # Note: We send synchronously or asynchronously before deletion completes
    send_email_async(clean_email, subject, html_content, text_content)
