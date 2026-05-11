# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time

TOKEN_PATH = '/auth/realms/powerflex/protocol/openid-connect/token'


class PowerFlexAPI:
    def __init__(
        self,
        http,
        gateway_url: str,
        logger,
        username: str | None = None,
        password: str | None = None,
        client_id: str = 'powerflexUI',
    ) -> None:
        self._http = http
        self._gateway_url = gateway_url
        self._username = username
        self._password = password
        self._client_id = client_id
        self._log = logger
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _ensure_authenticated(self) -> None:
        if not self._username:
            return
        if self._token and time() < self._token_expiry:
            return
        self._authenticate()

    def _authenticate(self) -> None:
        url = f'{self._gateway_url}{TOKEN_PATH}'
        response = self._http.post(
            url,
            data={
                'grant_type': 'password',
                'client_id': self._client_id,
                'username': self._username,
                'password': self._password,
            },
        )
        response.raise_for_status()
        data = response.json()
        self._token = data['access_token']
        expires_in = data.get('expires_in', 300)
        self._token_expiry = time() + expires_in - 30
        self._http.options['headers']['Authorization'] = f'Bearer {self._token}'
        self._log.debug('Refreshed PowerFlex auth token, expires in %ds', expires_in)

    def _get(self, path: str):
        self._ensure_authenticated()
        response = self._http.get(f"{self._gateway_url}{path}")
        response.raise_for_status()
        return response.json()

    def get_version(self) -> str:
        return self._get('/api/version')

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

    def get_alerts(self, since: str) -> list[dict]:
        query = f'/rest/v1/alerts?filter=last_updated ge {since}'
        response = self._get(query)
        results = response.get('results', []) if isinstance(response, dict) else []
        self._log.debug('Collected %d alerts', len(results))
        return results

    def get_events(self, since: str) -> list[dict]:
        query = f'/rest/v1/events?filter=timestamp ge {since}'
        response = self._get(query)
        results = response.get('results', []) if isinstance(response, dict) else []
        events = [e for e in results if e.get('severity') in ('CRITICAL', 'MAJOR')]
        self._log.debug('Collected %d events', len(events))
        return events
