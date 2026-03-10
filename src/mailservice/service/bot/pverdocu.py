import re

from bs4 import BeautifulSoup

from mailservice.constant import a360
from mailservice.exception.bot import ExtractEmailException
from mailservice.service.a360.hanlers import A360Hanler


class PverDocuBot(A360Hanler):
    def __init__(self, message: str, bot_username: str, bot_pw: str):
        A360Hanler.__init__(self, bot_username, bot_pw)
        self.msg = message

    def trigger_bot(self, queue_id: str):
        ntid, path = self.extract_mail_info(self.msg)
        if self.validate_ntid(ntid) and self.validate_path(path):
            data = {"workItems": [{"json": {"in_strNTID": ntid, "in_strSharedFolder": path}}]}
            url = a360.HOST + a360.PVER_DOCU_QUEUE.format(queue_id)
            self.send_request("POST", url, data)
        else:
            raise ExtractEmailException("Pver Docu bot - " + self.msg)

    @staticmethod
    def validate_ntid(ntid: str):
        pattern = re.compile("^[a-zA-Z]+\d+[a-zA-Z]+$")
        return bool(re.search(pattern, ntid))

    @staticmethod
    def validate_path(path: str):
        lpath = path.lower()
        return bool(
            "rb-powertrain-dashboard.bosch.com" in lpath
            or "si0vmc4579.de.bosch.com\\shared\\pver-docu_bot" in lpath
        )

    @staticmethod
    def extract_mail_info(content: str):
        soup = BeautifulSoup(content, "html.parser")
        # NTID
        ntid_match = re.search(r"\b[Nn][Tt][Ii][Dd]\s*:?\s*([A-Za-z0-9]+)\b", soup.get_text())

        if ntid_match:
            ntid = ntid_match.group(1)

        # Path
        path_match = re.search(r"\\{2}[A-Za-z0-9._-]+(\\[A-Za-z0-9._-]+)+", content)
        if path_match:
            path = path_match.group()
        return ntid, path
