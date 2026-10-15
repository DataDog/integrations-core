# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class PanosError(Exception):
    """Base class for every error raised while talking to PAN-OS."""


class PanosApiError(PanosError):
    """PAN-OS answered with status="error", or the body was not PAN-OS XML."""

    def __init__(self, code: str, msg: str, panos_response: bool = True):
        super().__init__(f'PAN-OS API error {code}: {msg}')
        self.code = code
        self.msg = msg
        self.panos_response = panos_response


class PanosAuthError(PanosApiError):
    """PAN-OS rejected the credentials or the API key: HTTP 403, or `code="403"` / `code="16"` in the body."""


class PanosUnreachable(PanosError):
    """A call did not get to PAN-OS: timeout, refused, DNS, TLS or a broken stream, all handled alike."""

    def __init__(self, msg: str, reason: str = ''):
        super().__init__(msg)
        self.reason = reason


class PanosSkipped(PanosUnreachable):
    """A call that was not made, because an earlier call of the run could not reach the device."""
