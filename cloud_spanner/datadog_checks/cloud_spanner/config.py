# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class QueryMetricsConfig:
    def __init__(self, raw: dict):
        self.enabled: bool = bool(raw.get('enabled', True))
        self.collection_interval: float = float(raw.get('collection_interval', 10.0))


class SpannerConfig:
    def __init__(self, instance: dict):
        self.project_id: str = instance['project_id']
        self.instance_id: str = instance['instance_id']
        self.database: str = instance['database']

        self.dbm_enabled: bool = bool(instance.get('dbm', False))
        self.credentials_path: str | None = instance.get('credentials_path')
        self.service: str | None = instance.get('service')
        self.tags: list[str] = list(instance.get('tags', []))

        self.query_metrics = QueryMetricsConfig(instance.get('query_metrics', {}))
