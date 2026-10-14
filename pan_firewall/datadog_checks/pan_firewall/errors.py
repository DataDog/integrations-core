# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class PanosError(Exception):
    """Base class for every error raised while talking to PAN-OS."""


class PanosApiError(PanosError):
    """PAN-OS answered with status="error", or with a body that is not XML.

    `code` is the response's `code` attribute (for example `'400'`), `'parse'` for a body that is not a PAN-OS
    response, or the HTTP status for an HTTP error with such a body. `panos_response` is False when the body was not a
    PAN-OS XML response (for example a proxy's HTML error page): PAN-OS itself did not answer.
    """

    def __init__(self, code: str, msg: str, panos_response: bool = True):
        super().__init__(f'PAN-OS API error {code}: {msg}')
        self.code = code
        self.msg = msg
        self.panos_response = panos_response


class PanosAuthError(PanosApiError):
    """PAN-OS rejected the credentials or the API key: HTTP 403, or `code="403"` / `code="16"` in the body."""


class PanosUnreachable(PanosError):
    """A call did not get to PAN-OS: a timeout, a refused connection, DNS, TLS or a broken stream, all alike.

    `reason` is the text of the underlying error, which says which it was (for example "Read timed out. (read
    timeout=30)"). The rest of the run is cut off: `PanosClient` fails every later call at once, with `PanosSkipped`.
    """

    def __init__(self, msg: str, reason: str = ''):
        super().__init__(msg)
        self.reason = reason


class PanosSkipped(PanosUnreachable):
    """A call that was not made, because an earlier call of the run could not reach the device."""
