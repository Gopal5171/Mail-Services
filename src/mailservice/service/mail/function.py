import logging
from pathlib import Path

from mailservice.constant.imap import IMAP_PORT, IMAP_SERVER
from mailservice.constant.smtp import ADMIN_EMAIL, SMTP_PORT, SMTP_SERVER
from mailservice.service.mail.receiver import EmailReceiver, Mail
from mailservice.service.mail.sender import EmailSender
from mailservice.util.common import get_credential

logger = logging.getLogger(__name__)


def fetch_mails_by_imap(username: str, access_token: str) -> list[Mail]:
    mail = EmailReceiver()
    mail.login(username, access_token, IMAP_SERVER, IMAP_PORT)
    mails = mail.get_mails(query="(UNSEEN)", mailbox="inbox")
    mail.logout()
    return mails


def mark_seen_and_move(username: str, access_token: str, mail_id: int, des_folder: str):
    mail = EmailReceiver()
    mail.login(username, access_token, IMAP_SERVER, IMAP_PORT)
    mail.copy_email_to_folder(str(mail_id), des_folder)
    mail.mark_seen_email(str(mail_id))
    mail.logout()


def send_error_to_admin(cred_name: str, msg: str):
    try:
        log_file = logger.handlers[1].baseFilename
    except:
        log_file = None
    username, password = get_credential(cred_name)
    mail = EmailSender(SMTP_SERVER, SMTP_PORT, username, password)
    template_path = Path(
        Path(__file__).parent.resolve().parent.parent, "constant", "admin_error.html"
    )
    with open(template_path) as f:
        content_html = f.read()
    content_html = content_html.format(msg)
    if log_file is not None:
        html_msg = mail.create_email(
            subject="Mailservice : Error",
            recipient=ADMIN_EMAIL,
            message_html=content_html,
            attachments=log_file,
        )
    else:
        html_msg = mail.create_email(
            subject="Mailservice : Error", recipient=ADMIN_EMAIL, message_html=content_html
        )
    mail.send_email(html_msg)


def send_to_user(user_email: str, cred_name: str, mail_type: str):
    username, password = get_credential(cred_name)
    mail = EmailSender(SMTP_SERVER, SMTP_PORT, username, password)
    # template_mail =
    if mail_type == "success":
        template_path = Path(
            Path(__file__).parent.resolve().parent.parent, "constant", "user_good.html"
        )
    elif mail_type == "error":
        template_path = Path(
            Path(__file__).parent.resolve().parent.parent, "constant", "user_failed.html"
        )

    with open(template_path) as f:
        content_html = f.read()

    html_msg = mail.create_email(
        subject="Mailservice : Notification", recipient=user_email, message_html=content_html
    )
    mail.send_email(html_msg)
