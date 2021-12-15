from typing import Set


class SecretsSanitizer:
    """
    A helper for sanitizing secrets (password, keys, ...) in text output.
    """

    REDACTED = '********'

    def __init__(self):
        # type: () -> None
        self.patterns = set()  # type: Set[str]

    def register(self, secret):
        # type: (str) -> None
        self.patterns.add(secret)

    def sanitize(self, text):
        # type: (str) -> str
        for pattern in self.patterns:
            text = text.replace(pattern, self.REDACTED)
        return text
