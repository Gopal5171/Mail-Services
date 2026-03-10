import re

from bs4 import BeautifulSoup

from mailservice.constant import a360
from mailservice.exception.bot import ExtractEmailException
from mailservice.service.a360.hanlers import A360Hanler


class IaBot(A360Hanler):
    def __init__(self, message: str, bot_username: str, bot_pw: str):
        A360Hanler.__init__(self, bot_username, bot_pw)
        self.msg = message

    def trigger_bot(self, mail_to: str):
        new_ifd, analyzed_ifd = self.extract_mail_info(self.msg)

        data = {
            "fileId": 1930633,
            "runAsUserIds": [self.id],
            "botInput": {
                "in_strAnaIssueFD": {"type": "STRING", "string": analyzed_ifd},
                "in_strNewIssueFD": {"type": "STRING", "string": new_ifd},
                "in_strEmailTo": {"type": "STRING", "string": mail_to},
            },
        }
        self.deploy(data)

    @staticmethod
    def extract_mail_info(content: str):
        soup = BeautifulSoup(content, "html.parser")
        # NTID
        new_ifd_match = re.search(r"New Issue-FD\s*:?\s*(RQONE\d+)", soup.get_text())

        if new_ifd_match:
            new_ifd = new_ifd_match.group(1)
        else:
            new_ifd = None

        # Path
        analyzed_ifd_match = re.search(r"Analyzed Issue-FD\s*:?\s*(RQONE\d+)", soup.get_text())

        if analyzed_ifd_match:
            analyzed_ifd = analyzed_ifd_match.group(1)
        else:
            analyzed_ifd = None

        if new_ifd == None or analyzed_ifd == None:
            raise ExtractEmailException("Impact Analysis bot - " + soup.get_text())

        return new_ifd, analyzed_ifd
