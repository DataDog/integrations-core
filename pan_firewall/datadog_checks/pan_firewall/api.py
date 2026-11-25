# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element

from datadog_checks.base.utils.http import RequestsWrapper, ResponseWrapper

from .constants import AUTH_ERROR_CODES, PARSE_ERROR_CODE
from .errors import PanosApiError, PanosAuthError, PanosError, PanosSkipped, PanosUnreachable
from .xml_utils import parse_response, text

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

    from .auth import KeyManager

KEY_HEADER = 'X-PAN-KEY'


def api_url(host: str) -> str:
    """Return the XML API endpoint of a PAN-OS device, always on port 443."""
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    return f'https://{host}/api/'


@contextmanager
def transport_errors(url: str) -> Iterator[None]:
    """Turn any OSError in the block (every `requests` exception is one) into PanosUnreachable, keeping its text.

    `from None`: the original exception holds the prepared request, whose headers carry the key.
    """
    host = urlsplit(url).netloc
    try:
        yield
    except OSError as e:
        raise PanosUnreachable(f'could not reach {host}: {e}', reason=str(e)) from None


def post_api(
    http: RequestsWrapper,
    url: str,
    data: dict[str, str],
    *,
    key: str | None = None,
) -> ResponseWrapper:
    """POST form `data` to the XML API. The key, when given, goes only in the `X-PAN-KEY` header."""
    options: dict[str, Any] = {'data': data}
    if key is not None:
        options['extra_headers'] = {KEY_HEADER: key}
    with transport_errors(url):
        return http.post(url, **options)


def read_response(resp: ResponseWrapper) -> Element:
    try:
        root = parse_response(resp.content)
    except PanosApiError as e:
        raise _classify(resp.status_code, e) from None
    if resp.status_code >= 400:
        raise _classify(resp.status_code, PanosApiError(str(resp.status_code), f'HTTP {resp.status_code}'))
    return root


# PAN-OS answers a call the role may not make with HTTP 403 and "... not authorized for user role.".
ROLE_REFUSAL = 'not authorized for user role'


def _classify(status_code: int, error: PanosApiError) -> PanosApiError:
    """HTTP 403 or an auth `code` is an auth failure, but only in a PAN-OS response: a proxy's error page says nothing
    about the key, so it must not trigger a renewal."""
    if not error.panos_response:
        if status_code >= 400:
            return PanosApiError(str(status_code), f'HTTP {status_code}: {error.msg}', panos_response=False)
        return error
    if ROLE_REFUSAL in (error.msg or '').lower():
        # The key works but the role lacks the permission (Report, config): a new key would be refused too.
        return error
    if status_code == 403 or error.code in AUTH_ERROR_CODES:
        # PAN's docs say code 16 means the role lacks permission, so a new key may not help. It is treated as an
        # expired key anyway, and the retry is bounded to one.
        code = error.code if error.code in AUTH_ERROR_CODES else '403'
        return PanosAuthError(code, error.msg or f'HTTP {status_code}')
    return error


@dataclass
class CallStats:
    """The calls since `PanosClient.start_run()`. `answered`: PAN-OS itself answered one, even with an error.
    `auth_rejected`: one failed auth after the renewal. `unreachable`: the reason of the first PanosUnreachable; once
    set, every call raises PanosSkipped until the next run."""

    calls: int = 0
    answered: bool = False
    auth_rejected: bool = False
    unreachable: str | None = None
    key_regenerated: bool = False


class PanosClient:
    """XML API client for one PAN-OS device (firewall or Panorama).

    At most `max_in_flight` calls at once, keygen and retry included. Once a call cannot reach the device, every later
    call raises PanosSkipped until `start_run()`: a hung device costs one timeout per run, not one per call.
    """

    def __init__(
        self,
        http: RequestsWrapper,
        host: str,
        keys: KeyManager,
        log: CheckLoggingAdapter,
        max_in_flight: int = 2,
    ):
        self._http = http
        self._host = host
        self._url = api_url(host)
        self._keys = keys
        self._log = log
        self._slots = threading.BoundedSemaphore(max_in_flight)
        self._stats = CallStats()
        self._stats_lock = threading.Lock()

    def op(self, cmd: str, *, renew_on_auth_error: bool = True) -> Element:
        """`renew_on_auth_error=False` is for an optional call whose permission refusal must not count as a rejected
        key: an auth error is raised as a plain PanosApiError, without renewing the key."""
        return self._send({'type': 'op', 'cmd': cmd}, read_response, renew_on_auth_error=renew_on_auth_error)

    def submit_job(self, params: dict[str, str]) -> str:
        """Submit an asynchronous job (report) and return its job id."""
        root = self._send(params, read_response)
        job_id = text(root, './result/job')
        if job_id is None:
            raise PanosApiError(PARSE_ERROR_CODE, 'job submission response has no job id')
        return job_id

    def get_job(self, job_type: str, job_id: str) -> tuple[str, Element]:
        """Return the job's status (`ACT`, `FIN`, ...) and the whole response."""
        root = self._send({'type': job_type, 'action': 'get', 'job-id': job_id}, read_response)
        status = text(root, './result/job/status')
        if status is None:
            raise PanosApiError(PARSE_ERROR_CODE, f'{job_type} job {job_id} response has no status')
        return status, root

    def start_run(self) -> None:
        """Start the stats of a new run, which also ends the fail-fast state and allows one keygen after a rejected one.
        Call it at the start of each run."""
        self._keys.allow_one_keygen()
        with self._stats_lock:
            self._stats = CallStats()

    @property
    def stats(self) -> CallStats:
        """A copy of the stats since `start_run()`."""
        with self._stats_lock:
            return dataclasses.replace(self._stats)

    def _send[T](
        self,
        params: dict[str, str],
        read: Callable[[ResponseWrapper], T],
        *,
        renew_on_auth_error: bool = True,
    ) -> T:
        """Make one call and `read` its response, renewing a rejected key once (unless `renew_on_auth_error` is off)."""
        with self._slots:
            with self._stats_lock:
                # Checked once the slot is held: a call waiting for the slot of the call that failed does not go out.
                if self._stats.unreachable is not None:
                    raise PanosSkipped(f'not calling {self._host}: an earlier call could not reach it')
                self._stats.calls += 1
            try:
                key = self._keys.key()
                try:
                    result = read(post_api(self._http, self._url, params, key=key))
                except PanosAuthError as e:
                    if not renew_on_auth_error:
                        raise PanosApiError(e.code, e.msg) from None
                    self._log.debug('PAN-OS %s rejected the API key (code %s), renewing it', self._host, e.code)
                    result = read(post_api(self._http, self._url, params, key=self._renew(key)))
            except PanosError as e:
                self._record(e)
                raise
            self._record(None)
            return result

    def _record(self, error: PanosError | None) -> None:
        """Record how a call ended; None means PAN-OS answered."""
        with self._stats_lock:
            if error is None or (isinstance(error, PanosApiError) and error.panos_response):
                self._stats.answered = True
            if isinstance(error, PanosAuthError):
                self._stats.auth_rejected = True
            if isinstance(error, PanosUnreachable) and self._stats.unreachable is None:
                self._stats.unreachable = error.reason

    def _renew(self, rejected: str) -> str:
        renewed = self._keys.renew(rejected)
        with self._stats_lock:
            self._stats.key_regenerated = True
        return renewed
