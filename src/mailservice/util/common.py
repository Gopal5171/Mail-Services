import datetime
import logging
from pathlib import Path
import time
from typing import Tuple
import urllib

import pytz

from mailservice.constant.proxy import BOSCH_PROXY
from mailservice.util.get_window_credential import get_generic_credential
import mailservice.util.sslcert
from mailservice.util.sslcert.cert import get_cert


def retry(times: int, exceptions: Exception, interval: int):
    """
    retry decorator
    Args:
        times (int): number of retry times
        exceptions (exception): exception that need to be retried.
    Returns:
        decorator (function): wrapper fuction
    Raise:
        None
    """

    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    logging.exception(
                        "Exception thrown when attempting to run %s, attempt "
                        "%d of %d" % (func, attempt, times)
                    )
                    attempt += 1
                    time.sleep(interval)

            return func(*args, **kwargs)

        return newfn

    return decorator


def verifi_request(host: str) -> str:
    """
    Check ssl certificate of host when sending http request
    Args:
        host: endpoint of http/https request
    Returns:
        cert_path: certitficate path
    Raise:
        None
    """
    cert_path = mailservice.util.sslcert.__path__[0] + "\\" + host + ".pem"
    if Path(cert_path).is_file():
        pass
    else:
        get_cert(cert_path)
    return cert_path


def raw_string(_str: str) -> str:
    """
    Return raw string in case of receiving paramater from A360 or command line.
    Args:
        _str: string input
    Returns:
        raw string
    Raise:
        None
    """
    return rf"{_str}"


def is_working_time():
    """
    Check current time is out of working time or on weekend. True -> working time, False: not working time
    Args:
        None
    Returns:
        Boolean
    Raise:
        None
    """
    timezone = "Asia/Singapore"
    tz = pytz.timezone(timezone)
    now = datetime.datetime.now(tz)
    current_time = now.time()
    current_day = now.weekday()  # Monday is 0 and Sunday is 6

    if current_day in [5, 6] or (
        current_time >= datetime.time(20) or current_time < datetime.time(6)
    ):
        return False  # It's a weekend and within the specified time range
    else:
        return True


def get_credential(cred_name: str) -> Tuple:
    """
    Get Generic Credential (username and pasword) from Windows Credential Manager
    Args:
        cred_name: credential name
    Returns:
        a tupe : (username,password)
    Raise:
        None
    """
    cred = get_generic_credential(cred_name.strip())
    if cred is None:
        raise Exception("Credential not found: " + cred_name)
    return cred[0], cred[1]


# Build proxy by username and password


def get_proxy() -> dict:
    username, password = get_credential("PROXY_CREDENTIAL")
    username = urllib.parse.quote(username)
    password = urllib.parse.quote(password)

    proxy_str = BOSCH_PROXY.format(username, password)
    proxy_str = "http://127.0.0.1:3128"
    proxies = {
        "http_proxy": proxy_str,
        "https_proxy": proxy_str,
        "proxy": proxy_str,
        "http": proxy_str,
        "https": proxy_str,
    }
    return proxies
