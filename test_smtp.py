import os, smtplib, ssl
from dotenv import load_dotenv
load_dotenv()

host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
user = os.environ["SMTP_USER"]
pw = os.environ["SMTP_PASSWORD"]

print("Trying port 465 (SSL)...")
try:
    with smtplib.SMTP_SSL(host, 465, timeout=20, context=ssl.create_default_context()) as s:
        s.login(user, pw)
        print("465 OK, login worked")
except Exception as e:
    print("465 failed:", type(e).__name__, e)

print("Trying port 587 (STARTTLS)...")
try:
    with smtplib.SMTP(host, 587, timeout=20) as s:
        s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
        s.login(user, pw)
        print("587 OK, login worked")
except Exception as e:
    print("587 failed:", type(e).__name__, e)