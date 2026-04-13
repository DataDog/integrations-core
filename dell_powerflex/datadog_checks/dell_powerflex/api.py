# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class PowerFlexAPI:
    def __init__(self, http, gateway_url: str) -> None:
        self._http = http
        self._gateway_url = gateway_url

    def get_systems(self) -> list[dict]:
        response = self._http.get(f"{self._gateway_url}/api/types/System/instances")
        response.raise_for_status()
        return response.json()

    def get_system_statistics(self, system_id: str) -> dict:
        url = f"{self._gateway_url}/api/instances/System::{system_id}/relationships/Statistics"
        response = self._http.get(url)
        response.raise_for_status()
        return response.json()

    def get_volumes(self) -> list[dict]:
        response = self._http.get(f"{self._gateway_url}/api/types/Volume/instances")
        response.raise_for_status()
        return response.json()

    def get_volume_statistics(self, volume_id: str) -> dict:
        url = f"{self._gateway_url}/api/instances/Volume::{volume_id}/relationships/Statistics"
        response = self._http.get(url)
        response.raise_for_status()
        return response.json()
