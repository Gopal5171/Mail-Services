import email
from email.message import Message
import imaplib
import logging

logger = logging.getLogger(__name__)


class Mail:
    def __init__(
        self,
        subject: str,
        sender: str,
        date: str,
        receiver: str,
        message: str,
        error: str,
        id: int,
    ):
        self.subject = subject.lower().strip()
        self.sender = sender
        self.date = date
        self.receiver = receiver
        self.message = message
        self.error = error
        self.id = id


class EmailReceiver:
    """
    A class for creating IMAP connection and get mails.

    """

    def __init__(self):
        """Constructor of an ImapGetMail."""
        self.logger = logger
        self.mail = None

    def login(self, username: str, token: str, server: str, port: int):
        """
        Raise:
            imaplib.error: AUTHENTICATE failed.
        """
        self.mail = imaplib.IMAP4_SSL(server, port)
        self.mail.authenticate("XOAUTH2", lambda x: self._generate_xoauth2_string(username, token))

    def logout(self):
        self.mail.close()
        self.mail.logout()

    def get_mails(self, query: str = "(UNSEEN)", mailbox: str = "inbox") -> list[Mail]:
        self.mail.select(mailbox=mailbox, readonly=1)
        (res, messages) = self.mail.search(None, query)
        if res == "OK":
            list_mail = []
            list_ID = self._get_mail_id(str(messages[0]))
            if len(list_ID) > 0:
                for mail_id in list_ID:
                    (typ, data) = self.mail.fetch(mail_id, "(RFC822)")
                    if typ == "OK":
                        try:
                            raw_email = email.message_from_bytes(data[0][1])
                            subject = raw_email["Subject"]
                            sender = self._extract_mail_subject(str(raw_email["From"]), "<", ">")
                            receiver = raw_email["To"]
                            date = raw_email["date"]
                            message = self._extract_body_email(raw_email)
                            mail = Mail(subject, sender, date, receiver, message, None, mail_id)
                            list_mail.append(mail)
                        except:
                            self.logger.exception(
                                "Not able to extract raw mail\n" + str(raw_email)
                            )

        return list_mail

    def mark_seen_email(self, mail_id: str):
        self.mail.select(mailbox="inbox", readonly=False)
        self.mail.store(mail_id, "+FLAGS", "\Seen")

    def copy_email_to_folder(self, mail_id: str, des_folder: str):
        self.mail.select(mailbox="inbox", readonly=False)
        self.mail.copy(mail_id, des_folder)

    def _get_mail_id(self, message: str):
        list_ID = []
        for i in message.split():
            mail_id = i.replace("b", "").replace("'", "")
            if mail_id.isnumeric():
                list_ID.append(mail_id)
        return list_ID

    def _extract_body_email(self, raw_email: Message):
        body = ""
        if raw_email.is_multipart():
            for part in raw_email.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))

                # skip any text/plain (txt) attachments
                if ctype == "text/plain" and "attachment" not in cdispo:
                    # print(part.get('Content-Transfer-Encoding'))
                    charset = part.get_content_charset()
                    body = part.get_payload(
                        decode=True
                    )  # decode based on 'Content-Transfer-Encoding' (base64)
                    body = body.decode(charset)  # decode based on 'charset' (utf-8)
                    break
        # not multipart - i.e. plain text, no attachments, keeping fingers crossed
        else:
            charset = raw_email.get_content_charset()
            body = raw_email.get_payload(decode=True)
            body = body.decode(charset)
        return body

    def _generate_xoauth2_string(self, user: str, token: str):
        auth_string = f"user={user}\1auth=Bearer {token}\1\1"
        return auth_string

    def _extract_mail_subject(self, s: str, first: str, last: str) -> str:
        try:
            start = s.index(first) + len(first)
            end = len(s) - 1 if not last else s.index(last, start)
            return s[start:end]
        except ValueError:
            self.logger.debug("Not able to extract mail subject: " + s)
            return s
