class AzureAuthenticationException(Exception):
    def __init__(self, response):
        if hasattr(response, "status_code") and hasattr(response, "text"):
            status = str(response.status_code) + " " + str(response.text)
        else:
            status = response
        super().__init__(f"Failed to authenticate Azure AD: \n{status}")
