import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from helpers.error import KnownError

def send_email_via_smtp(to_emails, subject, body, config):
    """
    Sends an email to one or multiple recipients.
    to_emails: Can be a single string "a@b.com" or a list ["a@b.com", "c@d.com"]
    """
    sender_email = config.get("EMAIL_USER")
    password = config.get("EMAIL_PASSWORD")
    smtp_server = config.get("SMTP_SERVER")
    smtp_port = int(config.get("SMTP_PORT", 465))

    if not sender_email or not password:
         raise KnownError("Email credentials not set. Run `ai config` first.")

    # Handle multiple recipients logic
    if isinstance(to_emails, str):
        # If comma separated string, split it
        recipient_list = [e.strip() for e in to_emails.split(',') if e.strip()]
    else:
        recipient_list = to_emails

    # The header needs a string "a@b.com, c@d.com"
    recipients_header = ", ".join(recipient_list)

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipients_header
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(sender_email, password)
        # sendmail expects a LIST of strings for the envelope
        server.sendmail(sender_email, recipient_list, msg.as_string())
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise KnownError("Authentication failed. Check your App Password.")
    except Exception as e:
        raise KnownError(f"Failed to send email: {e}")