# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""HTTP client for the Catalyst Center REST API.

The client owns three things collectors should never see: the token lifecycle, pagination
arithmetic, and the response envelope.

The envelope is the reason this layer exists. Catalyst Center returns errors in the same
``response`` slot it uses for real data, in at least six shapes, and one of them is an object
sitting exactly where a real object goes. A collector handed that error would iterate its keys
without raising anything and quietly record nothing. So the unwrapping happens once, here, and
each accessor knows the shape it expects.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, TypeGuard

from .constants import (
    AUTH_ENDPOINT,
    DEFAULT_PAGE_LIMIT,
    ENDPOINT_PAGE_LIMITS,
    ERROR_OBJECT_KEYS,
    FIRST_OFFSET,
    TOKEN_LIFETIME_SECONDS,
)
from .errors import CatalystApiError

DEFAULT_MAX_PAGES = 1000
DEFAULT_REFRESH_BUFFER_SECONDS = 300

# Catalyst Center publishes no X-RateLimit-* headers, so a 429 is the only signal that the
# budget is gone, and the budget itself varies by endpoint (documented as 20-500 per minute).
# Retries are bounded rather than persistent: a throttled appliance is made worse by hammering.
MAX_THROTTLE_RETRIES = 3
THROTTLE_BASE_DELAY_SECONDS = 1.0
THROTTLE_MAX_DELAY_SECONDS = 30.0


class CatalystCenterClient:
    """Authenticated, paginating, envelope-aware client for one Catalyst Center appliance."""

    def __init__(
        self,
        instance: dict[str, Any],
        http: Any,
        log: logging.Logger | None = None,
    ) -> None:
        self.base_url = self._normalize_host(instance['catalyst_center_host'])
        self.http = http
        self.log = log or logging.getLogger(__name__)

        self._username = instance.get('catalyst_center_username')
        self._password = instance.get('catalyst_center_password')
        self._max_pages = instance.get('max_pages') or DEFAULT_MAX_PAGES
        self._refresh_buffer = self._resolve_refresh_buffer(
            instance.get('token_refresh_buffer_seconds') or DEFAULT_REFRESH_BUFFER_SECONDS
        )

        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self.auth_count = 0

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Accept a bare hostname or a full URL, always return an https base URL."""
        host = host.rstrip('/')
        if host.startswith(('http://', 'https://')):
            return host
        return f'https://{host}'

    def _resolve_refresh_buffer(self, buffer_seconds: int) -> int:
        """Clamp a buffer that would leave no usable token life.

        A buffer at or above the token lifetime means every token is considered stale the
        instant it is minted, which produces an authentication loop rather than an error.
        """
        if buffer_seconds >= TOKEN_LIFETIME_SECONDS:
            fallback = TOKEN_LIFETIME_SECONDS // 6
            self.log.warning(
                'token_refresh_buffer_seconds (%s) is not shorter than the %ss token lifetime; falling back to %ss',
                buffer_seconds,
                TOKEN_LIFETIME_SECONDS,
                fallback,
            )
            return fallback
        return buffer_seconds

    # -- authentication ---------------------------------------------------------------

    def _authenticate(self) -> None:
        response = self.http.post(f'{self.base_url}{AUTH_ENDPOINT}', auth=(self._username, self._password))
        if response.status_code >= 400:
            raise CatalystApiError(
                'Catalyst Center authentication failed',
                error_code=response.status_code,
                correlation_id=self._correlation_id(response),
            )
        token = response.json().get('Token')
        if not token:
            raise CatalystApiError('Catalyst Center authentication returned no Token field')

        self._token = token
        self._token_expires_at = time.monotonic() + TOKEN_LIFETIME_SECONDS - self._refresh_buffer
        self.auth_count += 1

    def _ensure_token(self) -> None:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            self._authenticate()

    # -- request plumbing -------------------------------------------------------------

    @staticmethod
    def _correlation_id(response: Any) -> str | None:
        return getattr(response, 'headers', {}).get('x-correlation-id')

    def _auth_headers(self) -> dict[str, str]:
        return {'X-Auth-Token': self._token or ''}

    def _throttle_delay(self, response: Any, attempt: int) -> float:
        """How long to wait after a 429.

        Cisco's own ``Retry-After`` is preferred when present, since it reflects the appliance's
        actual budget window; otherwise back off exponentially with jitter so that several
        collectors throttled at once do not retry in lockstep.
        """
        retry_after = getattr(response, 'headers', {}).get('Retry-After')
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                self.log.debug('Could not parse Retry-After value %r; falling back to backoff', retry_after)

        delay = min(THROTTLE_BASE_DELAY_SECONDS * (2**attempt), THROTTLE_MAX_DELAY_SECONDS)
        return delay + random.uniform(0, delay / 2)

    def _get_body(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Issue one authenticated GET and return the whole validated body.

        Re-authenticates exactly once on a 401, retries a bounded number of times on a 429, and
        raises on every other failure shape.
        """
        url = f'{self.base_url}{path}'

        for attempt in range(MAX_THROTTLE_RETRIES):
            self._ensure_token()
            response = self.http.get(url, params=params, extra_headers=self._auth_headers())
            if response.status_code != 429:
                break
            if attempt == MAX_THROTTLE_RETRIES - 1:
                # Out of attempts. Sleeping now would only delay the error.
                break
            delay = self._throttle_delay(response, attempt)
            self.log.warning(
                'Catalyst Center rate limited %s (attempt %s/%s); waiting %.1fs',
                path,
                attempt + 1,
                MAX_THROTTLE_RETRIES,
                delay,
            )
            time.sleep(delay)

        if response.status_code == 429:
            raise CatalystApiError(
                f'Catalyst Center rate limit not cleared for {path} after {MAX_THROTTLE_RETRIES} attempts',
                error_code=429,
                correlation_id=self._correlation_id(response),
            )

        if response.status_code == 401:
            # The token aged out mid-cycle. Refresh once and retry with the new token; never loop.
            self._authenticate()
            response = self.http.get(url, params=params, extra_headers=self._auth_headers())
            if response.status_code == 401:
                raise CatalystApiError(
                    f'Catalyst Center rejected authentication twice for {path}',
                    error_code=401,
                    correlation_id=self._correlation_id(response),
                )

        if response.status_code >= 400:
            # The body of a 4xx carries Cisco's own errorCode, message and detail, and that
            # sentence is the difference between "HTTP 400" and "deviceId is not in UUID format".
            # Prefer it, and fall back to the status code only when the body says nothing useful.
            self._raise_from_status_body(response, path)

        return self._unwrap(response, path)

    def _raise_from_status_body(self, response: Any, path: str) -> None:
        """Always raises. Prefers the error described in the body over the bare status code."""
        try:
            described = self._error_from_body(response.json(), path, self._correlation_id(response))
        except Exception:  # noqa: BLE001 - an unparseable body must not mask the HTTP failure
            self.log.debug('Could not parse the error body for %s', path, exc_info=True)
            described = None

        raise described or CatalystApiError(
            f'Catalyst Center returned HTTP {response.status_code} for {path}',
            error_code=response.status_code,
            correlation_id=self._correlation_id(response),
        )

    # -- envelope handling ------------------------------------------------------------

    @staticmethod
    def _is_error_object(candidate: Any) -> TypeGuard[dict[str, Any]]:
        """An error object carries errorCode and nothing a real record would carry.

        Matching on the exact key set rather than the presence of ``errorCode`` alone keeps a
        legitimate record that happens to have a similarly named field from being mistaken for
        a failure.
        """
        return isinstance(candidate, dict) and 'errorCode' in candidate and set(candidate).issubset(ERROR_OBJECT_KEYS)

    @staticmethod
    def _as_error(error: dict[str, Any], path: str, correlation_id: str | None) -> CatalystApiError:
        return CatalystApiError(
            f'Catalyst Center reported an error for {path}: {error.get("message")}',
            error_code=error.get('errorCode'),
            detail=error.get('detail'),
            correlation_id=correlation_id,
        )

    def _error_from_body(self, body: Any, path: str, correlation_id: str | None) -> CatalystApiError | None:
        """Return the error this body describes, or None if it describes data.

        Kept separate from :meth:`_unwrap` so that an HTTP failure carrying an uninformative body
        still reports its status code rather than a misleading complaint about the body's shape.
        """
        if not isinstance(body, dict):
            return None

        # An unregistered route answers {"error": ...} with no `response` key at all.
        if 'error' in body and 'response' not in body:
            return CatalystApiError(
                f'Catalyst Center reported an error for {path}: {body["error"]}',
                correlation_id=correlation_id,
            )

        # A soft failure: HTTP 200, an empty response, and the reason in errorMessage. Checking
        # the status code alone records zero records and reports success.
        if body.get('errorMessage'):
            return CatalystApiError(
                f'Catalyst Center reported an error for {path}: {body["errorMessage"].strip()}',
                correlation_id=correlation_id,
            )

        payload = body.get('response')

        if self._is_error_object(payload):
            return self._as_error(payload, path, correlation_id)

        # Validation failures arrive as a list of error objects, sometimes more than one: a bad
        # time window returns two `errorCode 2046` entries, only the first of which has a message.
        if isinstance(payload, list) and payload and all(self._is_error_object(item) for item in payload):
            described = next((item for item in payload if item.get('message')), payload[0])
            return self._as_error(described, path, correlation_id)

        return None

    def _unwrap(self, response: Any, path: str) -> Any:
        """Validate the body and return it whole, raising on every failure shape seen on the wire.

        Returns the parsed body -- a dict for an enveloped response, or a list for the endpoints
        that answer with a bare JSON array. Extracting ``response`` from it is the caller's job,
        because some endpoints put their payload beside that key rather than inside it.
        """
        body = response.json()

        # A bare array has no envelope to inspect.
        if isinstance(body, list):
            return body

        if not isinstance(body, dict):
            raise CatalystApiError(f'Catalyst Center returned an unexpected body type for {path}')

        error = self._error_from_body(body, path, self._correlation_id(response))
        if error is not None:
            raise error

        return body

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Fetch an endpoint and return the contents of its ``response`` key."""
        body = self._get_body(path, params)
        if isinstance(body, list):
            return body
        if 'response' not in body:
            raise CatalystApiError(f'Catalyst Center returned no response field for {path}')
        return body['response']

    # -- typed accessors --------------------------------------------------------------

    def _post_body(self, path: str, body: dict[str, Any]) -> Any:
        """Issue one authenticated POST and return the whole validated body.

        The analytics endpoints are POST-only. Unlike :meth:`_get_body` this does not retry on a
        401: an analytics query is not idempotent in cost, and a stale token surfacing here means
        the cycle is already long enough that retrying is the wrong instinct.
        """
        self._ensure_token()
        response = self.http.post(f'{self.base_url}{path}', json=body, extra_headers=self._auth_headers())

        if response.status_code >= 400:
            self._raise_from_status_body(response, path)

        return self._unwrap(response, path)

    def post_object(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Run an analytics query and return its ``response`` object.

        The summary and top-N endpoints answer with an object holding ``attributes``,
        ``aggregateAttributes`` and ``groups`` -- each of which is ``null`` rather than empty when
        there is no data, so callers must guard accordingly.
        """
        body_payload = self._post_body(path, body)
        if isinstance(body_payload, list):
            raise CatalystApiError(f'Expected an envelope from {path}, got a bare array')
        if 'response' not in body_payload:
            raise CatalystApiError(f'Catalyst Center returned no response field for {path}')

        payload = body_payload['response']
        if not isinstance(payload, dict):
            raise CatalystApiError(f'Expected an object from {path}, got {type(payload).__name__}')
        return payload

    def get_envelope(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch an endpoint whose payload sits beside ``response`` rather than inside it.

        ``intent/network-health`` is the case that requires this: its totals and its per-category
        distribution are top-level siblings, while ``response`` holds a time-bucketed series.
        """
        body = self._get_body(path, params)
        if not isinstance(body, dict):
            raise CatalystApiError(f'Expected an object from {path}, got {type(body).__name__}')
        return body

    def get_list(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Page through a list endpoint and return every record.

        Pagination is 1-based, and the page size is a property of the endpoint rather than
        something a caller chooses, so it is looked up here instead of being an argument.
        Termination is on a short page: ``page.count`` is the collection total, not the page
        size, so terminating on it either truncates or loops forever.
        """
        limit = ENDPOINT_PAGE_LIMITS.get(path, DEFAULT_PAGE_LIMIT)
        offset = FIRST_OFFSET
        records: list[dict[str, Any]] = []

        for _ in range(self._max_pages):
            page_params = {**(params or {}), 'limit': limit, 'offset': offset}
            page = self._get(path, page_params)
            if not isinstance(page, list):
                raise CatalystApiError(f'Expected a list from {path}, got {type(page).__name__}')

            records.extend(page)
            if len(page) < limit:
                return records
            offset += limit
        else:
            self.log.warning(
                'Stopped paginating %s after max_pages (%s); results are incomplete',
                path,
                self._max_pages,
            )

        return records

    def get_object(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch a single object, such as a device's stack detail."""
        payload = self._get(path, params)
        if not isinstance(payload, dict):
            raise CatalystApiError(f'Expected an object from {path}, got {type(payload).__name__}')
        return payload

    def get_scalar(self, path: str, params: dict[str, Any] | None = None) -> int:
        """Fetch a count endpoint, whose response field is a bare integer."""
        payload = self._get(path, params)
        if not isinstance(payload, int):
            raise CatalystApiError(f'Expected an integer from {path}, got {type(payload).__name__}')
        return payload

    def get_bare_array(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Fetch an endpoint that answers with a naked JSON array and no envelope."""
        payload = self._get(path, params)
        if not isinstance(payload, list):
            raise CatalystApiError(f'Expected an array from {path}, got {type(payload).__name__}')
        return payload
