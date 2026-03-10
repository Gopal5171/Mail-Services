import logging
from pathlib import Path

import requests

from mailservice.constant.azure import (
    CONNECT_TIMEOUT,
    IMAP_SCOPE,
    READ_TIMEOUT,
    URL,
)
from mailservice.exception.api import ApiHostException, ApiProxyException
from mailservice.exception.azure_authen import AzureAuthenticationException
from mailservice.util.common import get_credential, get_proxy, raw_string, verifi_request


def send_request(config: dict, grant_type: str, code: str) -> dict:
    url = URL.replace("tenant_id", config["TENANT_ID"])

    header = {"Content-Type": "application/x-www-form-urlencoded"}

    data = {
        "client_id": config["CLIENT_ID"],
        "scope": IMAP_SCOPE,
        "client_secret": config["CLIENT_SECRET"],
        "redirect_uri": config["REDIRECT_URL"],
        "grant_type": grant_type,
    }

    if grant_type == "authorization_code":
        data.update({"code": code})
    else:
        data.update({"refresh_token": code})

    try:
        response = requests.post(
            url=url,
            headers=header,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            data=data,
            verify=verifi_request("microsoftonline"),
            proxies=get_proxy(),
            auth=get_credential("PROXY_CREDENTIAL"),
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 407:
            raise ApiProxyException("Failed to connect Azure Activate Directory")
        else:
            raise AzureAuthenticationException(response)

    except OSError as e:
        msg = str(getattr(e, "message", repr(e)))
        logging.error("server error" + url)
        raise ApiHostException(msg)


def get_access_token(config: dict, author_code: str):
    json_resp = send_request(config, "authorization_code", author_code)
    return json_resp


def refresh_access_token(config: dict):
    if not Path(raw_string(config["REFRESH_CODE_FILE"])).is_file:
        raise AzureAuthenticationException("REFRESH_CODE_FILE not found ")

    with open(raw_string(config["REFRESH_CODE_FILE"])) as f:
        refresh_token_code = f.read()

    json_resp = send_request(config, "refresh_token", refresh_token_code)
    access_token = json_resp["access_token"]
    time_exries = float(json_resp["expires_in"])
    return access_token, time_exries
