# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from requests import Response

from datadog_checks.base.utils.http import RequestsWrapper

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


class _BaseClient:
    """Shared HTTP client with transparent 401 re-login."""

    def __init__(self, http: RequestsWrapper, base_url: str) -> None:
        self._http = http
        self._base_url = base_url
        self._creds: tuple[str, str] | None = None

    def login(self, username: str, password: str) -> None:
        self._do_login(username, password)
        self._creds = (username, password)

    def _do_login(self, username: str, password: str) -> None:
        raise NotImplementedError

    def _request(self, method: str, path: str, *, raise_on_error: bool = True, **kwargs: Any) -> Response:
        """Issue an HTTP request, transparently re-logging in once on 401 (expired session)."""
        url = f'{self._base_url}{path}'
        send = getattr(self._http, method)
        resp = send(url, **kwargs)
        if resp.status_code == 401 and self._creds is not None:
            self._do_login(*self._creds)
            resp = send(url, **kwargs)
        if raise_on_error:
            resp.raise_for_status()
        return resp


class OrchestratorClient(_BaseClient):
    """HTTP client for the HPE Aruba EdgeConnect orchestrator API."""

    def __init__(self, http: RequestsWrapper, orch_ip: str) -> None:
        super().__init__(http, f'https://{orch_ip}')

    def _do_login(self, username: str, password: str) -> None:
        resp = self._http.post(
            f'{self._base_url}/gms/rest/authentication/login',
            json={'user': username, 'password': password},
        )
        resp.raise_for_status()
        csrf_token = self._http.session.cookies.get('orchCsrfToken')
        if csrf_token:
            self._http.session.headers.update({'X-XSRF-TOKEN': csrf_token})

    def get_appliances(self) -> list[dict[str, Any]]:
        resp = self._request('get', '/gms/rest/appliance')
        return resp.json()

    def get_overlay_config(self) -> tuple[dict[str, str], dict[str, str]]:
        """Fetch overlay configuration and derive id -> name mappings for overlays and traffic classes."""
        resp = self._request('get', '/gms/rest/gms/overlays/config')
        data = resp.json()
        overlay_map: dict[str, str] = {}
        traffic_class_map: dict[str, str] = {}
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                name = entry.get('name')
                overlay_id = entry.get('id')
                if overlay_id is not None:
                    overlay_id_str = str(overlay_id)
                    overlay_map[overlay_id_str] = name or overlay_id_str
                traffic_class = entry.get('trafficClass')
                if traffic_class is not None and name:
                    traffic_class_map.setdefault(str(traffic_class), name)
        return overlay_map, traffic_class_map


class ApplianceClient(_BaseClient):
    """HTTP client for an individual EdgeConnect appliance."""

    def __init__(self, http: RequestsWrapper, app_ip: str, logger: CheckLoggingAdapter) -> None:
        super().__init__(http, f'https://{app_ip}')
        self._app_ip = app_ip
        self._log = logger

    @property
    def app_ip(self) -> str:
        return self._app_ip

    def _do_login(self, username: str, password: str) -> None:
        resp = self._http.post(
            f'{self._base_url}/rest/json/login',
            json={'user': username, 'password': password},
        )
        resp.raise_for_status()
        csrf_token = self._http.session.cookies.get('edgeosCsrfToken')
        if csrf_token:
            self._http.session.headers.update({'X-XSRF-TOKEN': csrf_token})
        else:
            session_id = self._http.session.cookies.get('vxoaSessionID')
            if session_id:
                self._http.session.headers.update({'vxoaSessionID': session_id})

    def get_newest_timestamp(self) -> int:
        resp = self._request('get', '/rest/json/stats/minuteRange')
        payload = resp.json()
        newest = payload.get('newest')
        if newest is None:
            raise ValueError(
                f"Missing 'newest' field in minuteRange response from appliance {self._app_ip}: {payload!r}"
            )
        return int(newest)

    def get_minute_stats(self, filename: str) -> bytes:
        resp = self._request('get', f'/rest/json/stats/minuteStats/{filename}')
        return resp.content

    def get_network_interfaces(self) -> dict[str, Any]:
        resp = self._request('get', '/rest/json/networkInterfaces')
        return resp.json()

    def get_cpu_stats(self, timestamp: int) -> dict[str, Any] | None:
        # 403 here means the user lacks admin permission, not an expired session, so we don't retry.
        resp = self._request('get', f'/rest/json/cpustat?time={timestamp}', raise_on_error=False)
        if resp.status_code == 403:
            self._log.warning("403 fetching CPU stats from %s, no admin permissions", self._app_ip)
            return None
        resp.raise_for_status()
        return resp.json()

    def get_memory_stats(self) -> dict[str, Any]:
        resp = self._request('get', '/rest/json/memory')
        return resp.json()

    def get_disk_usage(self) -> dict[str, Any]:
        resp = self._request('get', '/rest/json/diskUsage')
        return resp.json()

    def get_alarms(self) -> dict[str, Any]:
        resp = self._request('get', '/rest/json/alarm')
        return resp.json()

    def get_system_info(self) -> dict[str, Any]:
        resp = self._request('get', '/rest/json/systemInfo')
        return resp.json()
