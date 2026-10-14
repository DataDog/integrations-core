# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .api import RequestCounter, api_url, post_api, read_response
from .constants import PARSE_ERROR_CODE
from .errors import PanosApiError, PanosAuthError
from .xml_utils import text

if TYPE_CHECKING:
    from datadog_checks.base.utils.http import RequestsWrapper


@dataclass(frozen=True)
class Credentials:
    username: str | None
    password: str | None = field(repr=False)
    api_key: str | None = field(repr=False)


class KeyManager:
    """Holds the API key of one PAN-OS device, in memory only.

    A rejected keygen latches: until `allow_one_keygen()` is called, `key()` and `regenerate()` raise PanosAuthError
    without contacting the device. Bad credentials cost one login attempt per run (one a minute at the default
    `min_collection_interval`) and never a retry loop within a run, but that rate can still reach a PAN-OS lockout
    threshold.
    """

    def __init__(self, http: RequestsWrapper, host: str, creds: Credentials, counter: RequestCounter | None = None):
        self._http = http
        self._host = host
        self._url = api_url(host)
        self._creds = creds
        self._counter = counter
        self._key: str | None = creds.api_key
        self._lock = threading.Lock()
        self._keygen_rejected = False

    def key(self) -> str:
        """Return the current key, generating one if none is held."""
        with self._lock:
            if self._key is None:
                self._raise_if_rejected()
                self._key = self._keygen()
            return self._key

    def regenerate(self) -> str:
        """Replace a rejected key with a new one; raise PanosAuthError if that is impossible or keygen fails."""
        with self._lock:
            if self._creds.api_key is not None:
                raise PanosAuthError('403', f'{self._host} rejected the configured API key, which is never renewed')
            self._raise_if_rejected()
            # The rejected key is dropped first, so a failed keygen leaves no key to retry with.
            self._key = None
            self._key = self._keygen()
            return self._key

    def allow_one_keygen(self) -> None:
        """Allow one new keygen after a rejected one. Called once at the start of each run."""
        with self._lock:
            self._keygen_rejected = False

    def _raise_if_rejected(self) -> None:
        if self._keygen_rejected:
            raise PanosAuthError('403', f'{self._host} rejected the credentials earlier; not retrying keygen')

    def _keygen(self) -> str:
        # The credentials go in the POST body, never in the URL.
        data = {'type': 'keygen', 'user': self._creds.username or '', 'password': self._creds.password or ''}
        resp = post_api(self._http, self._url, data, counter=self._counter)
        try:
            root = read_response(resp)
        except PanosAuthError as e:
            # A 403 from keygen itself means the credentials are wrong: retrying cannot help.
            self._keygen_rejected = True
            raise PanosAuthError(e.code, f'{self._host} rejected the credentials: {e.msg}') from None
        key = text(root, './result/key')
        if key is None:
            raise PanosApiError(PARSE_ERROR_CODE, f'keygen response from {self._host} has no key')
        return key
