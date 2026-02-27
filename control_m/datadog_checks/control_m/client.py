# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from datadog_checks.base.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from requests import Response

    from datadog_checks.base import AgentCheck


class ControlMClient:
    def __init__(self, check: AgentCheck) -> None:
        self._http = check.http
        self._log = check.log

        instance = check.instance

        self._api_endpoint = instance.get("control_m_api_endpoint", "").rstrip("/")
        if not self._api_endpoint:
            raise ConfigurationError("`control_m_api_endpoint` is required")

        # Static tokens can be created that have no expiration. This is the ideal approach for production.
        # But we can support both. The logic here is that we'll try first with a static token and if it fails,
        # we fall back to session login.
        headers = instance.get("headers", {})
        self._has_static_token = any(k.lower() == "authorization" for k in headers)

        self._username = instance.get("control_m_username")
        self._password = instance.get("control_m_password")
        self._has_credentials = bool(self._username and self._password)

        if not self._has_static_token and not self._has_credentials:
            if self._username or self._password:
                raise ConfigurationError(
                    "`control_m_username` and `control_m_password` must both be set or both be omitted"
                )
            raise ConfigurationError(
                "No authentication configured. Provide `headers` with an API token "
                "or both `control_m_username` and `control_m_password`"
            )

        self._use_session_login = not self._has_static_token and self._has_credentials

        self._token_lifetime = instance.get("token_lifetime_seconds", 1800)
        self._token_refresh_buffer = instance.get("token_refresh_buffer_seconds", 300)
        if self._token_refresh_buffer >= self._token_lifetime:
            self._token_refresh_buffer = self._token_lifetime // 6
            self._log.warning(
                "token_refresh_buffer_seconds >= token_lifetime_seconds; clamping refresh buffer to %d seconds",
                self._token_refresh_buffer,
            )

        self._token: str | None = None
        self._token_expiration = 0.0
        self._static_token_retry_after = 0.0
        self._static_token_retry_interval = 300.0

    @property
    def api_endpoint(self) -> str:
        return self._api_endpoint

    @property
    def use_session_login(self) -> bool:
        return self._use_session_login

    def auth_method_tag(self) -> str:
        # Added to keep track of which authentication method is being used.
        if self._use_session_login:
            return "auth_method:session_login"
        return "auth_method:static_token"

    def login(self) -> None:
        url = f"{self._api_endpoint}/session/login"
        payload = {"username": self._username, "password": self._password}

        try:
            response = self._http.post(url, json=payload)
        except OSError:
            self._log.error("Could not reach Control-M API at %s", url)
            raise

        if not response.ok:
            self._log.error("Control-M authentication failed (HTTP %s): %s", response.status_code, response.text)
            response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            self._log.error("Login response is not valid JSON: %s", response.text)
            raise

        token = data.get("token")
        if not token:
            raise ValueError(f"Login response did not contain a 'token' field: {data!r}")

        self._token = token
        self._token_expiration = time.monotonic() + self._token_lifetime
        self._log.debug("Obtained Control-M API token (valid for %d minutes)", self._token_lifetime // 60)

    def ensure_token(self) -> None:
        # Used in session login mode only. Refresh the token if it's about to expire.
        remaining = self._token_expiration - time.monotonic()
        if self._token is not None and remaining > self._token_refresh_buffer:
            return
        self._log.info("Refreshing Control-M API token")
        self.login()

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        request_fn = getattr(self._http, method)

        if self._use_session_login:
            if self._has_static_token and time.monotonic() >= self._static_token_retry_after:
                self._log.info("Retrying static token after cooldown")
                self._use_session_login = False
            else:
                return self._session_request(request_fn, url, **kwargs)

        response = request_fn(url, **kwargs)

        if response.status_code != 401:
            return response

        if not self._has_credentials:
            self._log.error("Token auth returned 401 and no credentials are configured for fallback")
            return response

        self._log.warning("Token auth returned 401; falling back to session login")
        self._use_session_login = True
        self._static_token_retry_after = time.monotonic() + self._static_token_retry_interval
        return self._session_request(request_fn, url, **kwargs)

    def _session_request(self, request_fn: Callable[..., Response], url: str, **kwargs: Any) -> Response:
        # Used in session login mode only. Make a request to the API using the session token.
        self.ensure_token()
        extra = {"Authorization": f"Bearer {self._token}"}
        response = request_fn(url, extra_headers=extra, **kwargs)

        if response.status_code == 401 and self._token is not None:
            self._log.info("Session token rejected (401); refreshing and retrying")
            self._token = None
            self.ensure_token()
            extra = {"Authorization": f"Bearer {self._token}"}
            response = request_fn(url, extra_headers=extra, **kwargs)

        return response
