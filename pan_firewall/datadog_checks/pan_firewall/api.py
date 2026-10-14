# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from datadog_checks.base.utils.http import RequestsWrapper

from .constants import AUTH_ERROR_CODES, PARSE_ERROR_CODE
from .errors import PanosApiError, PanosAuthError, PanosError, PanosSkipped, PanosUnreachable
from .xml_utils import check_response, parse_response, text

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

    from .auth import KeyManager

T = TypeVar('T')

KEY_HEADER = 'X-PAN-KEY'
STREAM_CHUNK_SIZE = 64 * 1024
# Paths, from the root, of a log job's entries and status.
LOG_ENTRY_PATH = ['response', 'result', 'log', 'logs', 'entry']
LOG_STATUS_PATH = ['response', 'result', 'job', 'status']


class Response(Protocol):
    """What the client reads of the response `RequestsWrapper.post` returns."""

    status_code: int
    content: bytes

    def iter_content(self, chunk_size: int) -> Iterator[bytes]: ...

    def close(self) -> None: ...

    def __enter__(self) -> Response: ...

    def __exit__(self, *exc_info: object) -> None: ...


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


class RequestCounter:
    """Counts every request `post_api` sends, keygen and retries included."""

    def __init__(self) -> None:
        self._count = 0
        self._lock = threading.Lock()

    def add(self) -> None:
        with self._lock:
            self._count += 1

    def take(self) -> int:
        with self._lock:
            count, self._count = self._count, 0
        return count


def post_api(
    http: RequestsWrapper,
    url: str,
    data: dict[str, str],
    *,
    key: str | None = None,
    stream: bool = False,
    counter: RequestCounter | None = None,
) -> Response:
    """POST form `data` to the XML API. The key, when given, goes only in the `X-PAN-KEY` header."""
    options: dict[str, Any] = {'data': data, 'stream': stream}
    if key is not None:
        options['extra_headers'] = {KEY_HEADER: key}
    if counter is not None:
        counter.add()
    with transport_errors(url):
        return http.post(url, **options)


def read_response(resp: Response) -> Element:
    try:
        root = parse_response(resp.content)
    except PanosApiError as e:
        raise _classify(resp.status_code, e) from None
    if resp.status_code >= 400:
        raise _classify(resp.status_code, PanosApiError(str(resp.status_code), f'HTTP {resp.status_code}'))
    return root


def _classify(status_code: int, error: PanosApiError) -> PanosApiError:
    """HTTP 403 or an auth `code` is an auth failure, but only in a PAN-OS response: a proxy's error page says nothing
    about the key, so it must not trigger a renewal."""
    if not error.panos_response:
        if status_code >= 400:
            return PanosApiError(str(status_code), f'HTTP {status_code}: {error.msg}', panos_response=False)
        return error
    if status_code == 403 or error.code in AUTH_ERROR_CODES:
        # Open question: PAN's docs say code 16 means the role lacks permission, so a new key may not help. The plan
        # treats it as an expired key; the retry is bounded to one.
        code = error.code if error.code in AUTH_ERROR_CODES else '403'
        return PanosAuthError(code, error.msg or f'HTTP {status_code}')
    return error


@dataclass
class CallStats:
    """The calls since `PanosClient.start_run()`. `answered`: PAN-OS itself answered one, even with an error.
    `auth_rejected`: one failed auth after the renewal. `unreachable`: the reason of the first PanosUnreachable."""

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
        counter: RequestCounter | None = None,
    ):
        self._http = http
        self._host = host
        self._url = api_url(host)
        self._keys = keys
        self._log = log
        self._counter = counter
        self._slots = threading.BoundedSemaphore(max_in_flight)
        self._renew_lock = threading.Lock()
        self._stats = CallStats()
        self._stats_lock = threading.Lock()

    def op(self, cmd: str) -> Element:
        return self._call({'type': 'op', 'cmd': cmd})

    def submit_job(self, params: dict[str, str]) -> str:
        """Submit an asynchronous job (log query, report) and return its job id."""
        root = self._call(params)
        job_id = text(root, './result/job')
        if job_id is None:
            raise PanosApiError(PARSE_ERROR_CODE, 'job submission response has no job id')
        return job_id

    def get_job(self, job_type: str, job_id: str) -> tuple[str, Element]:
        """Return the job's status (`ACT`, `FIN`, ...) and the whole response."""
        root = self._call({'type': job_type, 'action': 'get', 'job-id': job_id})
        status = text(root, './result/job/status')
        if status is None:
            raise PanosApiError(PARSE_ERROR_CODE, f'{job_type} job {job_id} response has no status')
        return status, root

    @contextmanager
    def open_log_job(self, job_id: str) -> Iterator[tuple[str, Iterator[Element]]]:
        """Read a log job with one streamed request: yield its status and, once `FIN`, its entries.

        Each entry is cleared when you advance, so read it first. The slot is held for the `with` block: do not call
        the client inside it.
        """
        with self._slots:
            self._fail_fast_if_unreachable()
            params = {'type': 'log', 'action': 'get', 'job-id': job_id}
            resp, root, events = self._authorized(lambda key: self._open_stream(params, key))
            with resp:
                try:
                    elements = _log_elements(root, events)
                    status_elem = next(elements, None)
                    if status_elem is None or status_elem.tag != 'status':
                        raise PanosApiError(PARSE_ERROR_CODE, f'log job {job_id} response has no status')
                    status = (status_elem.text or '').strip()
                    yield status, (elements if status == 'FIN' else iter(()))
                except PanosUnreachable as e:
                    # The stream broke after `_authorized` recorded the call: the rest of the run must know.
                    self._record_unreachable(e)
                    raise

    def _call(self, params: dict[str, str]) -> Element:
        with self._slots:
            self._fail_fast_if_unreachable()
            return self._authorized(
                lambda key: read_response(post_api(self._http, self._url, params, key=key, counter=self._counter))
            )

    def start_run(self) -> None:
        """Start the stats of a new run, which also ends the fail-fast state. Call it at the start of each run."""
        with self._stats_lock:
            self._stats = CallStats()

    @property
    def stats(self) -> CallStats:
        """A copy of the stats since `start_run()`."""
        with self._stats_lock:
            return dataclasses.replace(self._stats)

    @property
    def unreachable(self) -> str | None:
        """The reason of the run's first call that could not reach the device, or None."""
        with self._stats_lock:
            return self._stats.unreachable

    def _fail_fast_if_unreachable(self) -> None:
        # Checked once the slot is held: a call waiting for the slot of the call that failed does not go out either.
        if self.unreachable is not None:
            raise PanosSkipped(f'not calling {self._host}: an earlier call could not reach it')

    def _authorized(self, attempt: Callable[[str], T]) -> T:
        try:
            result = self._with_renewal(attempt)
        except PanosError as e:
            self._record(e)
            raise
        self._record(None)
        return result

    def _record_unreachable(self, error: PanosUnreachable) -> None:
        """Note a failure to reach the device that came after the call was recorded; it is not a call of its own."""
        with self._stats_lock:
            if self._stats.unreachable is None:
                self._stats.unreachable = error.reason

    def _record(self, error: PanosError | None) -> None:
        with self._stats_lock:
            self._stats.calls += 1
            if error is None or (isinstance(error, PanosApiError) and error.panos_response):
                self._stats.answered = True
            if isinstance(error, PanosAuthError):
                self._stats.auth_rejected = True
            if isinstance(error, PanosUnreachable) and self._stats.unreachable is None:
                self._stats.unreachable = error.reason

    def _with_renewal(self, attempt: Callable[[str], T]) -> T:
        key = self._keys.key()
        try:
            return attempt(key)
        except PanosAuthError as e:
            self._log.debug('PAN-OS %s rejected the API key (code %s), renewing it', self._host, e.code)
            return attempt(self._renew(key))

    def _renew(self, rejected: str) -> str:
        # Two calls in flight can be rejected with the same key; only the first regenerates it, and the other
        # retries with the new key. A fresh keygen can invalidate the key the first call just got.
        with self._renew_lock:
            current = self._keys.key()
            if current != rejected:
                return current
            renewed = self._keys.regenerate()
        with self._stats_lock:
            self._stats.key_regenerated = True
        return renewed

    def _open_stream(self, params: dict[str, str], key: str) -> tuple[Response, Element, Iterator[tuple[str, Element]]]:
        """Send a streamed request and read up to the root. An error response is raised here, inside `_authorized`, so
        a rejected key is renewed before any entry reaches the caller."""
        resp = post_api(self._http, self._url, params, key=key, stream=True, counter=self._counter)
        try:
            if resp.status_code >= 400:
                with transport_errors(self._url):
                    read_response(resp)
            events = self._stream_events(resp)
            first = next(events, None)
            if first is None:
                raise PanosApiError(PARSE_ERROR_CODE, 'response is empty', panos_response=False)
            root = first[1]
            if root.tag != 'response' or root.get('status') == 'error':
                for _ in events:
                    pass
                try:
                    check_response(root)
                except PanosApiError as e:
                    raise _classify(resp.status_code, e) from None
            return resp, root, events
        except BaseException:
            resp.close()
            raise

    def _stream_events(self, resp: Response) -> Iterator[tuple[str, Element]]:
        parser: ET.XMLPullParser[Element] = ET.XMLPullParser(events=('start', 'end'))
        try:
            with transport_errors(self._url):
                for chunk in resp.iter_content(chunk_size=STREAM_CHUNK_SIZE):
                    parser.feed(chunk)
                    yield from _element_events(parser)
            parser.close()
            yield from _element_events(parser)
        except ET.ParseError as e:
            raise PanosApiError(PARSE_ERROR_CODE, f'response is not valid XML: {e}', panos_response=False) from None


def _log_elements(root: Element, events: Iterator[tuple[str, Element]]) -> Iterator[Element]:
    """Yield `result/job/status`, then each log entry, which is cleared once the consumer advances."""
    path: list[str] = [root.tag]
    parent: Element | None = None
    seen_status = False
    for event, elem in events:
        if event == 'start':
            path.append(elem.tag)
            if path == LOG_ENTRY_PATH[:-1]:
                parent = elem
            continue
        if path == LOG_STATUS_PATH:
            seen_status = True
            yield elem
        elif path == LOG_ENTRY_PATH and parent is not None:
            if not seen_status:
                raise PanosApiError(PARSE_ERROR_CODE, 'log job response has entries before its status')
            yield elem
            elem.clear()
            parent.remove(elem)
        path.pop()


def _element_events(parser: ET.XMLPullParser[Element]) -> Iterator[tuple[str, Element]]:
    # Only `start` and `end` are requested, so every event carries an element; the check narrows the type.
    for item in parser.read_events():
        if len(item) == 2 and isinstance(item[1], Element):
            yield item[0], item[1]
