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

    def get_storage_pools(self) -> list[dict]:
        return self._get('/api/types/StoragePool/instances')

    def get_storage_pool_statistics(self, pool_id: str) -> dict:
        return self._get(f'/api/instances/StoragePool::{pool_id}/relationships/Statistics')

    def get_sdc_list(self) -> list[dict]:
        return self._get('/api/types/Sdc/instances')

    def get_sdc_statistics(self, sdc_id: str) -> dict:
        return self._get(f'/api/instances/Sdc::{sdc_id}/relationships/Statistics')

    def get_sds_list(self) -> list[dict]:
        return self._get('/api/types/Sds/instances')

    def get_sds_statistics(self, sds_id: str) -> dict:
        return self._get(f'/api/instances/Sds::{sds_id}/relationships/Statistics')

    def get_devices(self) -> list[dict]:
        return self._get('/api/types/Device/instances')

    def get_device_statistics(self, device_id: str) -> dict:
        return self._get(f'/api/instances/Device::{device_id}/relationships/Statistics')

    def get_protection_domains(self) -> list[dict]:
        return self._get('/api/types/ProtectionDomain/instances')

    def get_protection_domain_statistics(self, pd_id: str) -> dict:
        return self._get(f'/api/instances/ProtectionDomain::{pd_id}/relationships/Statistics')
