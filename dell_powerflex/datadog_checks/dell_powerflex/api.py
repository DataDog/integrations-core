# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class PowerFlexAPI:
    def __init__(self, http, gateway_url: str) -> None:
        self._http = http
        self._gateway_url = gateway_url

    def _get(self, path: str):
        response = self._http.get(f"{self._gateway_url}{path}")
        response.raise_for_status()
        return response.json()

    def get_systems(self) -> list[dict]:
        return self._get('/api/types/System/instances')

    def get_system_statistics(self, system_id: str) -> dict:
        return self._get(f'/api/instances/System::{system_id}/relationships/Statistics')

    def get_volumes(self) -> list[dict]:
        return self._get('/api/types/Volume/instances')

    def get_volume_statistics(self, volume_id: str) -> dict:
        return self._get(f'/api/instances/Volume::{volume_id}/relationships/Statistics')
