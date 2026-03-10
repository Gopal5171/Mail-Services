class ApiException(Exception):
    def __init__(self, msg, response):
        super().__init__(f"A request to the API was unsuccessful. {msg}")
        self.res = response


class ApiUriException(ApiException):
    def __init__(self, msg):
        super().__init__("Wrong URI format. Error: {}".format(msg))


class ApiHTTPException(ApiException):
    def __init__(self, response):
        super().__init__(
            "The server returned HTTP {} {}.".format(response.status_code, response.text), response
        )


class ApiInternalServerErrorException(ApiException):
    def __init__(self, response):
        super().__init__(
            "The server returned HTTP {} {}.".format(response.status_code, response.text), response
        )


class ApiHostException(Exception):
    def __init__(self, msg):
        super().__init__("Can not reach the server. Error: {}".format(msg))


class ApiProxyException(Exception):
    def __init__(self, msg):
        super(ApiHostException, self).__init__("Status code 407 - Proxy error: {}".format(msg))
