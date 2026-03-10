import re

from bs4 import BeautifulSoup

from mailservice.constant import a360
from mailservice.exception.bot import ExtractEmailException
from mailservice.service.a360.hanlers import A360Hanler

# run tealeaves : 1800243 procman : 1800244

TEALEAVES_BOT_ID = 1800243
PROCMAN_BOT_ID = 1800244


class BcPkgBot(A360Hanler):
    def __init__(self, message: str, bot_username: str, bot_pw: str):
        A360Hanler.__init__(self, bot_username, bot_pw)
        self.msg = message

    def trigger_bot(self, mail_to: str, file_id: int, rgx_pattern: str):
        scm_reference = self.extract_mail_info(self.msg, rgx_pattern)
        data = {
            "fileId": file_id,
            "runAsUserIds": [self.id],
            "botInput": {
                "in_strScmReference": {"type": "STRING", "string": scm_reference},
                "in_strNTID": {"type": "STRING", "string": mail_to},
            },
        }
        self.deploy(data)

    @staticmethod
    def extract_mail_info(content: str, regex_pattern: str):
        soup = BeautifulSoup(content, "html.parser")
        # NTID
        scm_reference_match = re.search(regex_pattern, soup.get_text())

        if scm_reference_match:
            scm_reference = scm_reference_match.group(1)
        else:
            scm_reference = None

        if scm_reference == None:
            raise ExtractEmailException("BC Packaging bot - Mail content: " + soup.get_text())

        return scm_reference


def trigger_tealeaves_bot(message: str, mail_to: str, bot_username: str, bot_pw: str):
    bot = BcPkgBot(message, bot_username, bot_pw)
    regex_pattern = r"PVER Name\s*:?\s*(PVER\s*:\s*[^;]+;\s*\d)"
    bot.trigger_bot(mail_to, TEALEAVES_BOT_ID, regex_pattern)


def trigger_procman_bot(message: str, mail_to: str, bot_username: str, bot_pw: str):
    bot = BcPkgBot(message, bot_username, bot_pw)
    regex_pattern = r"BC Name\s*:?\s*(PVER\s*:\s*[^;]+;\s*\d)"
    bot.trigger_bot(mail_to, PROCMAN_BOT_ID, regex_pattern)
