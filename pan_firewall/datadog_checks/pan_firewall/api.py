# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import requests
from requests import Response

from .constants import AUTH_ERROR_CODES, PARSE_ERROR_CODE
from .errors import PanosApiError, PanosAuthError, PanosConnectionError, PanosError, PanosTimeout
from .xml_utils import check_response, parse_response, text

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter
    from datadog_checks.base.utils.http import RequestsWrapper

    from .auth import KeyManager

__all__ = [
    'PanosApiError',
    'PanosAuthError',
    'PanosClient',
    'PanosConnectionError',
    'PanosError',
    'PanosTimeout',
    'api_url',
]

T = TypeVar('T')

KEY_HEADER = 'X-PAN-KEY'
STREAM_CHUNK_SIZE = 64 * 1024
# Element path, from the root, of the entries in a finished `type=log` job.
LOG_ENTRY_PATH = ['response', 'result', 'log', 'logs', 'entry']


def api_url(host: str, port: int) -> str:
    """Return the XML API endpoint of a PAN-OS device."""
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    return f'https://{host}:{port}/api/'


@contextmanager
def transport_errors(url: str) -> Iterator[None]:
    """Turn `requests` exceptions raised in the block into PanosTimeout or PanosConnectionError.

    The original exception is dropped (`from None`): it holds the prepared request, whose headers carry the key.
    """
    host = urlsplit(url).netloc
    try:
        yield
    # SSLError and ConnectTimeout subclass ConnectionError, so they are matched first.
    except requests.exceptions.SSLError as e:
        raise PanosConnectionError(f'TLS error talking to {host}: {e}') from None
    except requests.exceptions.Timeout:
        raise PanosTimeout(f'timed out talking to {host}') from None
    except requests.exceptions.ConnectionError as e:
        raise PanosConnectionError(f'cannot connect to {host}: {e}') from None
    except requests.exceptions.RequestException as e:
        raise PanosConnectionError(f'request to {host} failed: {e}') from None


def post_api(
    http: RequestsWrapper, url: str, data: dict[str, str], *, key: str | None = None, stream: bool = False
) -> Response:
    """POST form `data` to the XML API. The key, when given, goes only in the `X-PAN-KEY` header."""
    options: dict[str, Any] = {'data': data, 'stream': stream}
    if key is not None:
        options['extra_headers'] = {KEY_HEADER: key}
    with transport_errors(url):
        return http.post(url, **options)


def read_response(resp: Response) -> Element:
    """Return the root of a successful response; raise PanosAuthError or PanosApiError for a failed one."""
    try:
        root = parse_response(resp.content)
    except PanosApiError as e:
        raise _classify(resp.status_code, e) from None
    if resp.status_code >= 400:
        raise _classify(resp.status_code, PanosApiError(str(resp.status_code), f'HTTP {resp.status_code}'))
    return root


def _classify(status_code: int, error: PanosApiError) -> PanosApiError:
    """An HTTP 403, or a `code` PAN-OS uses for a rejected key, is an auth failure whatever the body says."""
    if status_code == 403 or error.code in AUTH_ERROR_CODES:
        # open question: PAN's docs say code 16 means the API role lacks permission for the command, so
        # regenerating the key may not help. It is handled like an expired key, as the plan specifies; the
        # retry is bounded to one, so the cost is one keygen per rejected call.
        code = error.code if error.code in AUTH_ERROR_CODES else '403'
        return PanosAuthError(code, error.msg or f'HTTP {status_code}')
    if error.code == PARSE_ERROR_CODE and status_code >= 400:
        return PanosApiError(str(status_code), f'HTTP {status_code}: {error.msg}')
    return error


class PanosClient:
    """XML API client for one PAN-OS device (firewall or Panorama).

    Every call holds one of `max_in_flight` slots for its whole duration, including any keygen and the retry, so
    the device never sees more than `max_in_flight` concurrent requests from this client.
    """

    def __init__(
        self,
        http: RequestsWrapper,
        host: str,
        port: int,
        keys: KeyManager,
        log: CheckLoggingAdapter,
        max_in_flight: int = 2,
    ):
        self._http = http
        self._host = host
        self._url = api_url(host, port)
        self._keys = keys
        self._log = log
        self._slots = threading.BoundedSemaphore(max_in_flight)
        self._renew_lock = threading.Lock()

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

    def iter_log_entries(self, job_id: str) -> Iterator[Element]:
        """Stream the `result/log/logs/entry` elements of a finished log job.

        Each entry is cleared once the caller asks for the next one, so memory stays bounded whatever the job size:
        read what you need from an entry before advancing. The call holds its slot until the generator is
        exhausted or closed.
        """
        params = {'type': 'log', 'action': 'get', 'job-id': job_id}
        with self._slots:
            resp, root, events = self._authorized(lambda key: self._open_stream(params, key))
            with resp:
                path: list[str] = [root.tag]
                parent: Element | None = None
                for event, elem in events:
                    if event == 'start':
                        path.append(elem.tag)
                        if path == LOG_ENTRY_PATH[:-1]:
                            parent = elem
                        continue
                    if path == LOG_ENTRY_PATH and parent is not None:
                        yield elem
                        elem.clear()
                        parent.remove(elem)
                    path.pop()

    def _call(self, params: dict[str, str]) -> Element:
        with self._slots:
            return self._authorized(lambda key: read_response(post_api(self._http, self._url, params, key=key)))

    def _authorized(self, attempt: Callable[[str], T]) -> T:
        """Run `attempt` with the current key; on an auth failure, renew the key once and run it again."""
        key = self._keys.key()
        try:
            result = attempt(key)
        except PanosAuthError as e:
            self._log.debug('PAN-OS %s rejected the API key (code %s), renewing it', self._host, e.code)
            result = attempt(self._renew(key))
        # A successful call proves the key is accepted, which is the only way a static key recovers.
        self._keys.auth_failed = False
        return result

    def _renew(self, rejected: str) -> str:
        # Two calls in flight can be rejected with the same key; only the first regenerates it, and the other
        # retries with the new key. A fresh keygen can invalidate the key the first call just got.
        with self._renew_lock:
            current = self._keys.key()
            if current != rejected:
                return current
            return self._keys.regenerate()

    def _open_stream(self, params: dict[str, str], key: str) -> tuple[Response, Element, Iterator[tuple[str, Element]]]:
        """Send a streamed request and read up to the root element.

        An error response is read to the end and raised here, inside `_authorized`, so a rejected key is renewed
        before any entry reaches the caller.
        """
        resp = post_api(self._http, self._url, params, key=key, stream=True)
        try:
            if resp.status_code >= 400:
                with transport_errors(self._url):
                    read_response(resp)
            events = self._stream_events(resp)
            first = next(events, None)
            if first is None:
                raise PanosApiError(PARSE_ERROR_CODE, 'response is empty')
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
            raise PanosApiError(PARSE_ERROR_CODE, f'response is not valid XML: {e}') from None


def _element_events(parser: ET.XMLPullParser[Element]) -> Iterator[tuple[str, Element]]:
    # Only `start` and `end` are requested, so every event carries an element; the check narrows the type.
    for item in parser.read_events():
        if len(item) == 2 and isinstance(item[1], Element):
            yield item[0], item[1]
