"""Defines EmailSender, a class for handling email sending."""

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib

logger = logging.getLogger(__name__)


def str_to_html(content):
    """Returns a string where line breaks and tabs are replaced by their HTML equivalents."""
    return content.replace("\n", "<br/>").replace("\t", "&emsp;")


class EmailSender:
    """
    A class for creating and sending mails.
    Arguments:
    """

    def __init__(self, server: str, port: int, username: str, password: str):
        """Constructor of an EmailSender."""
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.logger = logger

        self.mail_server = None

    def send_email(self, message: MIMEMultipart):
        """
        Sends the given mail.

        Creates an SMTP client session object and uses TLS to encrypt the connection to the outgoing mail server. Connects to the mail server for the duration of mail sending and then closes the connection (implicitly, when the `with` statement ends). If smtplib raises an exception indicating send failure (e.g. none of the recipients receive the mail), the event is logged and the exception re-raised.

        Arguments:
            message: A MIMEMultipart object representing the message to be sent. It should have its fields filled out; in particular, its recipients.

        Returns:
            None.

        Raises:
            SMTPException: Will be logged and re-raised if smtplib raises it.
        """

        try:
            # Initiate (unsecured) connection to an SMTP mail server
            self.mail_server = smtplib.SMTP(host=self.server, port=self.port)
            self.mail_server.ehlo()
            # Encrypt the connection by putting the SMTP connection in TLS mode. All SMTP commands afterwards will be encrypted.
            # Python's security considerations recommend usage of create_default_context() from the ssl module (loads system's trusted CA certificates and chooses cipher config).
            with self.mail_server as mail_server:
                # context = ssl.create_default_context(cafile=certifi.where())
                # mail_server.starttls(context=context)
                mail_server.starttls()
                mail_server.ehlo()
                mail_server.login(self.username, self.password)
                try:
                    mail_server.send_message(message)
                except smtplib.SMTPRecipientsRefused as e:
                    if not e.recipients:
                        self.logger.warning("Attempted to send email, but it had no recipients")
                    else:
                        self.logger.exception("One or more recipient refused")
                        raise

        except smtplib.SMTPException:
            self.logger.exception("Failed to send mail.")
            raise

    def create_email(
        self,
        subject,
        recipient,
        message_html,
        cc=None,
        bcc=None,
        attachments=None,
        sensitivity=None,
        message_text=None,
    ):
        """
        Create a MIMEMultipart object that can be passed to EmailSender.send_email.

        Arguments:
            subject: Subject of the message as a string.
            recipient: Recipient(s) of the message as a string. Separate multiple recipients with semicolons (;).
            message_html: Body of the message as a string. You may want to pass message_html through str_to_html first. If you want to get fancy, you may want to look into html template engines (e.g. jinja)
            cc: Carbon copy recipient(s) of the message as a string (optional). Separate multiple cc recipients with semicolons (;).
            bcc: Blind carbon copy recipient(s) of the message as a string (optional). Separate multiple bcc recipients with semicolons (;).
            attachments: Files to be attached, provided as an iterable of strings of absolute file paths (optional). This argument may be also provided as a string, indicating that there is only one attachment. Empty iterables, empty string and None may also be provided to indicate no attachment.
            sensitivity: Sensitivity flag (optional). Valid inputs are 'company-confidential', 'private', and 'personal'.
            message_text: Plaintext version of the message as a string (optional). May be useful if some of the recipients do not allow HTML formatted messages.

        Returns:
            The newly created message as a MIMEMultipart object.
        """
        html_msg = MIMEMultipart("alternative")
        html_msg["Subject"] = subject
        html_msg["From"] = self.username
        html_msg["To"] = recipient

        if cc:
            html_msg["Cc"] = cc

        if bcc:
            html_msg["Bcc"] = bcc

        if attachments:
            if isinstance(attachments, str):
                attachments = [attachments]
            for path in attachments:
                if os.path.isfile(path) and os.path.isabs(path):
                    self.logger.debug(f"Adding mail attachment: {path}")
                    # Open the file in binary mode and add it as application/octet-stream.
                    with open(path, "rb") as attachment:
                        attach_part = MIMEBase("application", "octet-stream")
                        attach_part.set_payload(attachment.read())

                    encoders.encode_base64(attach_part)
                    attach_part.add_header(
                        "Content-Disposition",
                        "attachment; filename={}".format(path.split("\\")[-1]),
                    )

                    html_msg.attach(attach_part)
                else:
                    self.logger.warning(
                        f"Expected email attachment as an absolute filepath to a file. Abandoning: {path}"
                    )

        if sensitivity in ("company-confidential", "private", "personal"):
            html_msg.add_header("Sensitivity", sensitivity)

        if message_text:
            html_msg.attach(MIMEText(message_text, "plain", "utf-8"))

        # Email client will try to render the last multipart attachment first, so add the actual message part here.
        html_msg.attach(MIMEText(message_html, "html", "utf-8"))

        self.logger.debug("Email created")
        return html_msg
