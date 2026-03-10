class ExtractEmailException(Exception):
    def __init__(self, msg):
        super().__init__(f"Faled to extract user email. Mail content {msg}")
