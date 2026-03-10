from typing import Optional

import requests
import urllib3

from mailservice.constant import a360
from mailservice.exception.api import (
    ApiHostException,
    ApiHTTPException,
    ApiInternalServerErrorException,
)
from mailservice.util.common import retry, verifi_request


class A360Hanler:
    def __init__(self, username: str, password: str) -> None:
        self.access_token, self.id = self._authenticatie(username, password)

    @retry(times=2, exceptions=ApiInternalServerErrorException, interval=10)
    def send_request(self, method: str, url: str, data: dict, headers: Optional[dict] = None):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if headers is None:
            headers = {
                "Content-Type": "application/json",
                "Host": "rpaproduction.emea.bosch.com",
                "X-Authorization": self.access_token,
            }
        try:
            if method == "POST":
                response = requests.post(
                    url, headers=headers, json=data, verify=verifi_request("rpaproduction")
                )
            if method == "PUT":
                response = requests.put(
                    url, headers=headers, json=data, verify=verifi_request("rpaproduction")
                )
        except OSError as e:
            msg = str(getattr(e, "message", repr(e)))
            raise ApiHostException(msg)

        if response.status_code == 200 or response.status_code == 201:
            return response
        elif response.status_code == 500:
            raise ApiInternalServerErrorException(response)
        else:
            raise ApiHTTPException(response)

    def _authenticatie(self, username, password):
        header = {"Content-Type": "application/json"}

        data = {"username": username, "password": password, "multipleLogin": "true"}
        url = a360.HOST + a360.AUTHEN
        response = self.send_request("POST", url, data, header)
        token = response.json()["token"]
        bot_id = response.json()["user"]["id"]
        return token, bot_id

    def deploy(self, data: dict):
        url = a360.HOST + a360.DEPLOY
        response = self.send_request("POST", url, data)
        return response
