# backend/app/services/email_service.py
"""
Email sending using Flask-Mail.
"""
from flask import current_app
from flask_mail import Message
from app import mail
import logging

logger = logging.getLogger(__name__)

def send_email(to, subject, body, html=None):
    """Send an email."""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            html=html,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise