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
