# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from requests.exceptions import HTTPError, RequestException

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.control_m.config_models import ConfigMixin

_SERVICE_CHECK_CAN_LOGIN = "can_login"
_SERVICE_CHECK_CAN_CONNECT = "can_connect"


class ControlMCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = "control_m"

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self._api_endpoint = self.instance.get("control_m_api_endpoint", "").rstrip("/")

        # Static tokens can be created that have no expiration. This is the ideal approach for production.
        # But we can support both. The logic here is that we'll try first with a static token and if it fails,
        # we fall back to session login.
        headers = self.instance.get("headers", {})
        self._has_static_token = any(k.lower() == "authorization" for k in headers)

        auth_token_config = self.instance.get("auth_token")
        self._has_auth_token = isinstance(auth_token_config, dict) and bool(auth_token_config)

        self._username = self.instance.get("control_m_username")
        self._password = self.instance.get("control_m_password")
        self._has_credentials = bool(self._username and self._password)

        has_token_auth = self._has_static_token or self._has_auth_token
        if not has_token_auth and not self._has_credentials:
            if self._username or self._password:
                raise ConfigurationError(
                    "`control_m_username` and `control_m_password` must both be set or both be omitted"
                )
            raise ConfigurationError(
                "No authentication configured. Provide `headers` with an API token, "
                "configure `auth_token` for dynamic token rotation, "
                "or set both `control_m_username` and `control_m_password`"
            )

        self._use_session_login = not has_token_auth and self._has_credentials

        # Tokens last 30 minutes by default. We can try refreshing them before they expire to interruptions.
        self._token_lifetime = self.instance.get("token_lifetime_seconds", 1800)
        self._token_refresh_buffer = self.instance.get("token_refresh_buffer_seconds", 300)

        self._base_tags = [f"control_m_instance:{self._api_endpoint}"]

        self._token = None
        self._token_expiration = 0.0

    def _login(self):
        # Used in session login mode only. Retrieve a new token from the API to use for subsequent requests.
        url = f"{self._api_endpoint}/session/login"
        payload = {"username": self._username, "password": self._password}

        try:
            response = self.http.post(url, json=payload)
            response.raise_for_status()
        except HTTPError as e:
            self.log.error("Control-M authentication failed (HTTP %s): %s", e.response.status_code, e.response.text)
            raise
        except RequestException:
            self.log.error("Could not reach Control-M API at %s", url)
            raise

        try:
            data = response.json()
        except ValueError:
            self.log.error("Login response is not valid JSON: %s", response.text)
            raise

        token = data.get("token")
        if not token:
            raise ValueError(f"Login response did not contain a 'token' field: {data!r}")

        self._token = token
        self._token_expiration = time.monotonic() + self._token_lifetime
        self.log.debug("Obtained Control-M API token (valid for %d minutes)", self._token_lifetime // 60)

    def _ensure_token(self):
        # Used in session login mode only. Refresh the token if it's about to expire.
        remaining = self._token_expiration - time.monotonic()
        if self._token is not None and remaining > self._token_refresh_buffer:
            return
        self.log.info("Refreshing Control-M API token")
        self._login()

    def _make_request(self, method, url, **kwargs):
        request_fn = getattr(self.http, method)

        if self._use_session_login:
            return self._make_session_request(request_fn, url, **kwargs)

        response = request_fn(url, **kwargs)

        if response.status_code != 401:
            return response

        if not self._has_credentials:
            self.log.error("Token auth returned 401 and no credentials are configured for fallback")
            return response

        self.log.warning("Token auth returned 401; falling back to session login")
        self._use_session_login = True
        return self._make_session_request(request_fn, url, **kwargs)

    def _make_session_request(self, request_fn, url, **kwargs):
        # Used in session login mode only. Make a request to the API using the session token.
        self._ensure_token()
        extra = {"Authorization": f"Bearer {self._token}"}
        response = request_fn(url, extra_headers=extra, **kwargs)

        if response.status_code == 401 and self._token is not None:
            self.log.info("Session token rejected (401); refreshing and retrying")
            self._token = None
            self._ensure_token()
            extra = {"Authorization": f"Bearer {self._token}"}
            response = request_fn(url, extra_headers=extra, **kwargs)

        return response

    def _auth_method_tag(self):
        if self._use_session_login:
            return "auth_method:session_login"
        if self._has_auth_token:
            return "auth_method:auth_token"
        return "auth_method:static_token"

    def _auth_tags(self):
        return self._base_tags + [self._auth_method_tag()]

    def check(self, _):
        auth_tags = self._auth_tags()

        if self._use_session_login:
            try:
                self._ensure_token()
            except Exception as e:
                self.service_check(
                    _SERVICE_CHECK_CAN_LOGIN,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.service_check(
                    _SERVICE_CHECK_CAN_CONNECT,
                    self.CRITICAL,
                    tags=auth_tags,
                    message=f"Failed to authenticate to Control-M API: {e}",
                )
                self.gauge("can_connect", 0, tags=auth_tags)
                raise
            self.service_check(_SERVICE_CHECK_CAN_LOGIN, self.OK, tags=auth_tags)

        try:
            response = self._make_request("get", f"{self._api_endpoint}/config/servers")
            response.raise_for_status()
            servers = response.json()
        except Exception as e:
            auth_tags = self._auth_tags()
            self.service_check(
                _SERVICE_CHECK_CAN_CONNECT,
                self.CRITICAL,
                tags=auth_tags,
                message=f"Failed to connect to Control-M API: {e}",
            )
            self.gauge("can_connect", 0, tags=auth_tags)
            raise

        auth_tags = self._auth_tags()
        self.service_check(_SERVICE_CHECK_CAN_CONNECT, self.OK, tags=auth_tags)
        self.gauge("can_connect", 1, tags=auth_tags)

        self._collect_metadata(servers)

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self, servers):
        # The /config/servers response is a list of server objects, each with
        # a "version" field (e.g. "9.0.21.080").  Report the first one found.
        if isinstance(servers, list):
            for server in servers:
                version = server.get("version")
                if version:
                    self.set_metadata("version", version)
                    self.log.debug("Collected Control-M version: %s", version)
                    return
        self.log.debug("Could not determine Control-M version from /config/servers response")
