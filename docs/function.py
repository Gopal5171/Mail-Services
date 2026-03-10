from mailservice.constant.imap import IMAP_PORT, IMAP_SERVER
from mailservice.service.mail.receiver import EmailReceiver, Mail


def fetch_mails_by_imap(username: str, access_token: str) -> list[Mail]:
    mail = EmailReceiver(username, access_token, IMAP_SERVER, IMAP_PORT)
    mail.login()
    mails = mail.get_mails(query="(UNSEEN)", mailbox="inbox")
    mail.logout()
    return mails


def mark_seen_email_by_imap(username: str, access_token: str, mail_id: int):
    mail = EmailReceiver(username, access_token, IMAP_SERVER, IMAP_PORT)
    mail.login()
    mail.mark_seen_email(mail_id=str(mail_id))
    mail.logout()


def send_error_to_admin():
    None
