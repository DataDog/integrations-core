# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class PanosError(Exception):
    """Base class for every error raised while talking to PAN-OS."""


class PanosApiError(PanosError):
    """PAN-OS answered with status="error", or with a body that is not XML.

    `code` is the response's `code` attribute (for example `'400'`), or `'parse'` for a non-XML body.
    """

    def __init__(self, code: str, msg: str):
        super().__init__(f'PAN-OS API error {code}: {msg}')
        self.code = code
        self.msg = msg


class PanosAuthError(PanosApiError):
    """PAN-OS rejected the credentials or the API key: HTTP 403, or `code="403"` / `code="16"` in the body."""


class PanosTimeout(PanosError):
    """A call to PAN-OS did not answer within the configured timeout."""


class PanosConnectionError(PanosError):
    """PAN-OS could not be reached: connection refused, DNS, TLS handshake, or a broken stream."""
