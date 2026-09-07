"""Minimal transactional email delivery for account recovery."""
import html
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("email")
settings = get_settings()


def send_password_reset_email(*, recipient: str, reset_url: str) -> None:
    """Send a password-reset email. SMTP must be configured outside development."""
    if not settings.SMTP_HOST:
        if settings.ENVIRONMENT == "development":
            logger.info("Password-reset delivery is not configured; reset URL generated for %s", recipient)
            return
        raise RuntimeError("SMTP_HOST is not configured")

    safe_url = html.escape(reset_url, quote=True)
    message = EmailMessage()
    message["Subject"] = "Reset your Perception password"
    message["From"] = settings.MAIL_FROM
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Perception password.\n\n"
        f"Use this link within {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes:\n{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )
    message.add_alternative(
        f"<p>We received a request to reset your Perception password.</p>"
        f"<p><a href=\"{safe_url}\">Reset your password</a></p>"
        f"<p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>"
        "<p>If you did not request this, you can safely ignore this email.</p>",
        subtype="html",
    )

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
