# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from datadog_checks.base import AgentCheck

from .config import SpannerConfig
from .query_metrics import SpannerQueryMetrics


class SpannerCheck(AgentCheck):
    __NAMESPACE__ = 'gcp.spanner'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._config = SpannerConfig(self.instance)
        self._query_metrics = SpannerQueryMetrics(self)
        self._client = None

    @property
    def reported_hostname(self) -> str:
        return f"{self._config.project_id}:{self._config.instance_id}"

    @property
    def cloud_metadata(self) -> dict:
        return {
            'gcp': {
                'project_id': self._config.project_id,
                'instance_id': self._config.instance_id,
            }
        }

    def check(self, _) -> None:
        if not self._config.dbm_enabled:
            self.log.debug("DBM not enabled, skipping")
            return
        client = self._get_spanner_client()
        self._query_metrics.collect(client)

    def _get_spanner_client(self):
        if self._client is None:
            self._client = self._create_spanner_client()
        return self._client

    def _create_spanner_client(self):
        from google.cloud import spanner

        kwargs: dict = {'project': self._config.project_id}
        if self._config.credentials_path:
            from google.oauth2 import service_account

            kwargs['credentials'] = service_account.Credentials.from_service_account_file(
                self._config.credentials_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform'],
            )
        return spanner.Client(**kwargs)
