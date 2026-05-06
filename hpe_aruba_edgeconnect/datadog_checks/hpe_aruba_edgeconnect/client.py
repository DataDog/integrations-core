# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datadog_checks.base.utils.http import RequestsWrapper

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


class OrchestratorClient:
    """HTTP client for the HPE Aruba EdgeConnect orchestrator API."""

    def __init__(self, http: RequestsWrapper, orch_ip: str) -> None:
        self._http = http
        self._base_url = f'https://{orch_ip}'

    def login(self, username: str, password: str) -> None:
        resp = self._http.post(
            f'{self._base_url}/gms/rest/authentication/login',
            json={'user': username, 'password': password},
        )
        resp.raise_for_status()
        csrf_token = self._http.session.cookies.get('orchCsrfToken')
        if csrf_token:
            self._http.session.headers.update({'X-XSRF-TOKEN': csrf_token})

    def get_appliances(self) -> list[dict[str, Any]]:
        resp = self._http.get(f'{self._base_url}/gms/rest/appliance')
        resp.raise_for_status()
        return resp.json()

    def get_overlay_config(self) -> dict[str, str]:
        resp = self._http.get(f'{self._base_url}/gms/rest/gms/overlays/config')
        resp.raise_for_status()
        data = resp.json()
        overlay_map: dict[str, str] = {}
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                overlay_id = entry.get('id')
                if overlay_id is None:
                    continue
                overlay_id_str = str(overlay_id)
                overlay_map[overlay_id_str] = entry.get('name', overlay_id_str)
        return overlay_map


class ApplianceClient:
    """HTTP client for an individual EdgeConnect appliance."""

    def __init__(self, http: RequestsWrapper, app_ip: str, logger: CheckLoggingAdapter) -> None:
        self._http = http
        self._base_url = f'https://{app_ip}'
        self._app_ip = app_ip
        self._log = logger

    @property
    def app_ip(self) -> str:
        return self._app_ip

    def login(self, username: str, password: str) -> None:
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
        resp = self._http.get(f'{self._base_url}/rest/json/stats/minuteRange')
        resp.raise_for_status()
        return resp.json()['newest']

    def get_minute_stats(self, filename: str) -> bytes:
        resp = self._http.get(
            f'{self._base_url}/rest/json/stats/minuteStats/{filename}',
        )
        resp.raise_for_status()
        return resp.content

    def get_network_interfaces(self) -> dict[str, Any]:
        resp = self._http.get(f'{self._base_url}/rest/json/networkInterfaces')
        resp.raise_for_status()
        return resp.json()

    def get_cpu_stats(self, timestamp: int) -> dict[str, Any] | None:
        resp = self._http.get(f'{self._base_url}/rest/json/cpustat?time={timestamp}')
        if resp.status_code == 403:
            self._log.warning("403 fetching CPU stats from %s, no admin permissions", self._app_ip)
            return None
        resp.raise_for_status()
        return resp.json()

    def get_memory_stats(self) -> dict[str, Any]:
        resp = self._http.get(f'{self._base_url}/rest/json/memory')
        resp.raise_for_status()
        return resp.json()

    def get_disk_usage(self) -> dict[str, Any]:
        resp = self._http.get(f'{self._base_url}/rest/json/diskUsage')
        resp.raise_for_status()
        return resp.json()

    def get_alarms(self) -> dict[str, Any]:
        resp = self._http.get(f'{self._base_url}/rest/json/alarm')
        resp.raise_for_status()
        return resp.json()
