# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .api import api_url, post_api, read_response
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
    """The API key of one PAN-OS device, in memory only.

    A rejected keygen latches until `allow_one_keygen()`, which `PanosClient.start_run()` calls: bad credentials cost
    one login attempt per run, never a retry loop, though one a minute can still reach a PAN-OS lockout threshold.
    """

    def __init__(self, http: RequestsWrapper, host: str, creds: Credentials):
        self._http = http
        self._host = host
        self._url = api_url(host)
        self._creds = creds
        self._key: str | None = creds.api_key
        self._lock = threading.Lock()
        self._keygen_rejected = False

    def key(self) -> str:
        with self._lock:
            if self._key is None:
                self._raise_if_rejected()
                self._key = self._keygen()
            return self._key

    def renew(self, rejected: str) -> str:
        """Return the key to retry with after `rejected` was refused; raise PanosAuthError if that is impossible (a
        static key) or keygen fails.

        Two calls in flight can be rejected with the same key: only the first regenerates it and the other gets the
        new key, because a second keygen can invalidate the key the first call just got.
        """
        with self._lock:
            if self._key is not None and self._key != rejected:
                return self._key
            if self._creds.api_key is not None:
                raise PanosAuthError('403', f'{self._host} rejected the configured API key, which is never renewed')
            self._raise_if_rejected()
            self._key = None
            self._key = self._keygen()
            return self._key

    def allow_one_keygen(self) -> None:
        """Allow one keygen after a rejected one."""
        with self._lock:
            self._keygen_rejected = False

    def _raise_if_rejected(self) -> None:
        if self._keygen_rejected:
            raise PanosAuthError('403', f'{self._host} rejected the credentials earlier; not retrying keygen')

    def _keygen(self) -> str:
        # The credentials go in the POST body, never in the URL.
        data = {'type': 'keygen', 'user': self._creds.username or '', 'password': self._creds.password or ''}
        resp = post_api(self._http, self._url, data)
        try:
            root = read_response(resp)
        except PanosAuthError as e:
            self._keygen_rejected = True
            raise PanosAuthError(e.code, f'{self._host} rejected the credentials: {e.msg}') from None
        key = text(root, './result/key')
        if key is None:
            raise PanosApiError(PARSE_ERROR_CODE, f'keygen response from {self._host} has no key')
        return key
