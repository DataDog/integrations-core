# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from .api import post_api, read_response
from .constants import PARSE_ERROR_CODE
from .errors import PanosApiError, PanosAuthError
from .xml_utils import text

if TYPE_CHECKING:
    from datadog_checks.base.utils.http import RequestsWrapper


@dataclass(frozen=True)
class Credentials:
    """Either `username` and `password` (a key is generated), or `api_key` (used as-is, never renewed)."""

    username: str | None
    password: str | None = field(repr=False)
    api_key: str | None = field(repr=False)


class KeyManager:
    """Holds the API key of one PAN-OS device, in memory only.

    `auth_failed` is True once the device rejected the credentials: a keygen answered with an auth error, or the
    static `api_key` was rejected. A successful keygen resets it.

    A rejected keygen latches: until `reset_failure()` is called, `key()` and `regenerate()` raise PanosAuthError
    without contacting the device, so bad credentials cost one login attempt per run and never trigger a lockout.
    """

    def __init__(self, http: RequestsWrapper, base_url: str, creds: Credentials):
        if creds.api_key is None and not (creds.username and creds.password):
            raise ValueError('Credentials need either `username` and `password`, or `api_key`')
        self._http = http
        self._base_url = base_url
        self._host = urlsplit(base_url).netloc
        self._creds = creds
        self._key: str | None = creds.api_key
        self._lock = threading.Lock()
        self._keygen_rejected = False
        self.auth_failed = False
        # True once `regenerate()` replaced the key, until `take_regenerated()`: a key the device rejected after it
        # had accepted it may mean the device is another one now.
        self._regenerated = False

    def take_regenerated(self) -> bool:
        """Return whether the key was regenerated since the last call, and clear the flag."""
        with self._lock:
            regenerated, self._regenerated = self._regenerated, False
        return regenerated

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
                self.auth_failed = True
                raise PanosAuthError('403', f'{self._host} rejected the configured API key, which is never renewed')
            self._raise_if_rejected()
            # The rejected key is dropped first, so a failed keygen leaves no key to retry with.
            self._key = None
            self._key = self._keygen()
            self._regenerated = True
            return self._key

    def reset_failure(self) -> None:
        """Allow one new keygen after a rejected one. Called once at the start of each run; `auth_failed` is kept."""
        with self._lock:
            self._keygen_rejected = False

    def _raise_if_rejected(self) -> None:
        if self._keygen_rejected:
            raise PanosAuthError('403', f'{self._host} rejected the credentials earlier; not retrying keygen')

    def _keygen(self) -> str:
        # The credentials go in the POST body, never in the URL.
        data = {'type': 'keygen', 'user': self._creds.username or '', 'password': self._creds.password or ''}
        resp = post_api(self._http, self._base_url, data)
        try:
            root = read_response(resp)
        except PanosAuthError as e:
            # A 403 from keygen itself means the credentials are wrong: retrying cannot help.
            self._keygen_rejected = True
            self.auth_failed = True
            raise PanosAuthError(e.code, f'{self._host} rejected the credentials: {e.msg}') from None
        key = text(root, './result/key')
        if key is None:
            raise PanosApiError(PARSE_ERROR_CODE, f'keygen response from {self._host} has no key')
        self.auth_failed = False
        return key
