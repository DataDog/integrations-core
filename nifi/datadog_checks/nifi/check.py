# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# ABOUTME: Datadog Agent check for Apache NiFi.
# ABOUTME: Polls the NiFi REST API to collect JVM, flow, queue, processor, and bulletin data.
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck

from .api import NiFiApi
from .constants import (
    BULLETIN_ALERT_TYPE,
    BULLETIN_LEVEL_ORDER,
    CONNECTION_METRICS,
    FLOW_STATUS_METRICS,
    PROCESS_GROUP_METRICS,
    PROCESSOR_METRICS,
    REPO_METRICS,
    RUN_STATUS_MAP,
    SYSTEM_CPU_METRICS,
    SYSTEM_GC_METRICS,
    SYSTEM_JVM_METRICS,
)


class NifiCheck(AgentCheck):
    __NAMESPACE__ = 'nifi'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # NiFi uses its own token-based auth (POST /access/token), not HTTP Basic Auth.
        # Only disable RequestsWrapper's automatic auth when NiFi credentials are provided,
        # so that reverse-proxy auth configurations (Basic, Digest, Kerberos) still work.
        if self.instance.get('username') and self.instance.get('password'):
            self.http.options['auth'] = None
        self._api = None

    def _get_api(self):
        if self._api is None:
            # api_url is a required config field; fail fast with KeyError if missing.
            self._api = NiFiApi(
                api_url=self.instance['api_url'],
                http=self.http,
                log=self.log,
                username=self.instance.get('username'),
                password=self.instance.get('password'),
            )
        return self._api

    def check(self, _):
        api = self._get_api()
        try:
            version = api.get_about()
            base_tags = [f'nifi_version:{version}'] + self.instance.get('tags', [])

            self._collect_system_diagnostics(api, base_tags)
            self._collect_flow_status(api, base_tags)
            self._collect_process_group_metrics(api, base_tags)
            self._collect_cluster_health(api, base_tags)

            if self.instance.get('collect_bulletins', True):
                self._collect_bulletins(api, base_tags)

            self.service_check('can_connect', AgentCheck.OK, tags=base_tags)
        except Exception:
            self.log.exception('NiFi check failed')
            self.service_check('can_connect', AgentCheck.CRITICAL, tags=self.instance.get('tags', []))
            raise

    @staticmethod
    def _parse_utilization(value):
        """Parse a percentage string like '16.0%' to a float. Returns 0.0 for unavailable values."""
        if not value or value == 'N/A':
            return 0.0
        if isinstance(value, str) and value.endswith('%'):
            return float(value.rstrip('%'))
        return float(value)

    def _submit_gauges(self, snap, metrics, tags, prefix=''):
        """Submit gauge metrics from a snapshot dict using a mapping of (api_key, metric_name)."""
        for api_key, metric_name in metrics:
            name = f'{prefix}.{metric_name}' if prefix else metric_name
            self.gauge(name, snap.get(api_key, 0), tags=tags)

    def _submit_monotonic_counts(self, snap, metrics, tags):
        """Submit monotonic count metrics from a snapshot dict using a mapping of (api_key, metric_name)."""
        for api_key, metric_name in metrics:
            self.monotonic_count(metric_name, snap.get(api_key, 0), tags=tags)

    def _collect_repo_metrics(self, repo, prefix, tags):
        """Submit gauge metrics for a storage repository (used_space, free_space, utilization)."""
        self._submit_gauges(repo, REPO_METRICS, tags, prefix=prefix)
        util = repo.get('utilization', '0%')
        self.gauge(f'{prefix}.utilization', self._parse_utilization(util), tags=tags)

    def _collect_system_diagnostics(self, api, base_tags):
        data = api.get_system_diagnostics()
        snap = data.get('systemDiagnostics', {}).get('aggregateSnapshot', {})

        self._submit_gauges(snap, SYSTEM_CPU_METRICS, base_tags)
        self._submit_gauges(snap, SYSTEM_JVM_METRICS, base_tags)
        heap_util = snap.get('heapUtilization', '0%')
        self.gauge('system.jvm.heap_utilization', self._parse_utilization(heap_util), tags=base_tags)

        for gc in snap.get('garbageCollection', []):
            gc_tags = base_tags + [f'gc_name:{gc.get("name", "unknown")}']
            self._submit_monotonic_counts(gc, SYSTEM_GC_METRICS, gc_tags)

        self._collect_repo_metrics(snap.get('flowFileRepositoryStorageUsage', {}), 'system.flowfile_repo', base_tags)
        for repo in snap.get('contentRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo.get("identifier", "unknown")}']
            self._collect_repo_metrics(repo, 'system.content_repo', repo_tags)
        for repo in snap.get('provenanceRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo.get("identifier", "unknown")}']
            self._collect_repo_metrics(repo, 'system.provenance_repo', repo_tags)

    def _collect_flow_status(self, api, base_tags):
        data = api.get_flow_status()
        status = data.get('controllerStatus', {})
        self._submit_gauges(status, FLOW_STATUS_METRICS, base_tags)

    def _collect_process_group_metrics(self, api, base_tags):
        process_groups = self.instance.get('process_groups', ['root'])
        visited = set()
        all_connections = []
        all_processors = []
        for pg_id in process_groups:
            data = api.get_process_group_status(pg_id)
            pg_status = data.get('processGroupStatus', {})
            self._emit_process_group(pg_status, base_tags, visited, all_connections, all_processors)

        if self.instance.get('collect_connection_metrics', False):
            self._emit_connection_metrics(all_connections, base_tags)
        if self.instance.get('collect_processor_metrics', False):
            self._emit_processor_metrics(all_processors, base_tags)

    def _emit_process_group(self, pg_status, base_tags, visited, all_connections, all_processors):
        """Emit metrics for a process group, collect child entity data, and recurse."""
        snap = pg_status.get('aggregateSnapshot', {})
        pg_id = snap.get('id')
        if pg_id and pg_id in visited:
            return
        if pg_id:
            visited.add(pg_id)

        pg_tags = base_tags + [
            f'process_group_name:{snap.get("name", "unknown")}',
            f'process_group_id:{pg_id or "unknown"}',
        ]

        self._submit_gauges(snap, PROCESS_GROUP_METRICS, pg_tags)

        all_connections.extend(snap.get('connectionStatusSnapshots', []))
        all_processors.extend(snap.get('processorStatusSnapshots', []))

        for child in snap.get('processGroupStatusSnapshots', []):
            child_status = child.get('processGroupStatusSnapshot', {})
            if child_status:
                self._emit_process_group(
                    {'aggregateSnapshot': child_status}, base_tags, visited, all_connections, all_processors
                )

    def _emit_connection_metrics(self, all_connections, base_tags):
        max_connections = self.instance.get('max_connections', 200)
        connections = sorted(
            all_connections,
            key=lambda c: c.get('connectionStatusSnapshot', {}).get('flowFilesQueued', 0),
            reverse=True,
        )[:max_connections]

        if len(all_connections) > max_connections:
            self.log.warning(
                'Truncated connections from %d to %d (max_connections)',
                len(all_connections),
                max_connections,
            )

        for conn in connections:
            snap = conn.get('connectionStatusSnapshot', {})
            conn_tags = base_tags + [
                f'connection_name:{snap.get("name", "unknown")}',
                f'source_name:{snap.get("sourceName", "unknown")}',
                f'destination_name:{snap.get("destinationName", "unknown")}',
                f'process_group_id:{snap.get("groupId", "unknown")}',
            ]
            self._submit_gauges(snap, CONNECTION_METRICS, conn_tags)

    def _emit_processor_metrics(self, all_processors, base_tags):
        max_processors = self.instance.get('max_processors', 200)
        processors = sorted(
            all_processors,
            key=lambda p: p.get('processorStatusSnapshot', {}).get('taskCount', 0),
            reverse=True,
        )[:max_processors]

        if len(all_processors) > max_processors:
            self.log.warning(
                'Truncated processors from %d to %d (max_processors)',
                len(all_processors),
                max_processors,
            )

        for proc in processors:
            snap = proc.get('processorStatusSnapshot', {})
            proc_tags = base_tags + [
                f'processor_name:{snap.get("name", "unknown")}',
                f'processor_type:{snap.get("type", "unknown")}',
                f'process_group_id:{snap.get("groupId", "unknown")}',
            ]
            self._submit_gauges(snap, PROCESSOR_METRICS, proc_tags)
            run_status = RUN_STATUS_MAP.get(snap.get('runStatus', ''), -1)
            self.gauge('processor.run_status', run_status, tags=proc_tags)

    _CACHE_KEY_LAST_BULLETIN_ID = 'last_bulletin_id'

    def _collect_bulletins(self, api, base_tags):
        data = api.get_bulletin_board()
        bulletins = data.get('bulletinBoard', {}).get('bulletins', [])

        last_id_str = self.read_persistent_cache(self._CACHE_KEY_LAST_BULLETIN_ID)
        last_id = int(last_id_str) if last_id_str else -1

        # NiFi bulletin IDs are auto-incrementing and reset to 0 on restart.
        # Detect the reset so post-restart bulletins aren't silently dropped.
        if last_id >= 0 and bulletins:
            max_board_id = max(b.get('id', 0) for b in bulletins)
            if max_board_id < last_id:
                self.log.info(
                    'Bulletin ID reset detected (cached=%d, max_on_board=%d); clearing watermark',
                    last_id,
                    max_board_id,
                )
                last_id = -1

        min_level = self.instance.get('bulletin_min_level', 'WARNING')
        min_level_order = BULLETIN_LEVEL_ORDER.get(min_level, 2)
        max_per_cycle = self.instance.get('max_bulletins_per_cycle', 100)

        new_bulletins = [
            b
            for b in bulletins
            if b.get('id', 0) > last_id
            and b.get('canRead', False)
            and BULLETIN_LEVEL_ORDER.get(b.get('bulletin', {}).get('level', ''), 0) >= min_level_order
        ]
        new_bulletins.sort(key=lambda b: b.get('id', 0))
        new_bulletins = new_bulletins[:max_per_cycle]

        for entry in new_bulletins:
            bulletin = entry.get('bulletin', {})
            level = bulletin.get('level', 'WARNING')
            source_name = bulletin.get('sourceName', 'unknown')

            ts = None
            ts_iso = bulletin.get('timestampIso') or entry.get('timestampIso')
            if ts_iso:
                try:
                    dt = datetime.fromisoformat(ts_iso.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    ts = int(dt.timestamp())
                except (ValueError, OSError):
                    self.log.debug('Could not parse bulletin timestamp: %s', ts_iso)

            event_tags = base_tags + [
                f'bulletin_level:{level}',
                f'source_name:{source_name}',
                f'source_type:{bulletin.get("sourceType", "unknown")}',
            ]

            self.event(
                {
                    'timestamp': ts,
                    'event_type': 'nifi.bulletin',
                    'msg_title': f'NiFi Bulletin: {source_name} [{level}]',
                    'msg_text': bulletin.get('message', ''),
                    'alert_type': BULLETIN_ALERT_TYPE.get(level, 'warning'),
                    'source_type_name': 'nifi',
                    'tags': event_tags,
                }
            )

        if new_bulletins:
            max_id = max(b.get('id', 0) for b in new_bulletins)
            self.write_persistent_cache(self._CACHE_KEY_LAST_BULLETIN_ID, str(max_id))

    def _collect_cluster_health(self, api, base_tags):
        data = api.get_cluster_summary()
        summary = data.get('clusterSummary', {})
        if not summary.get('clustered', False):
            return

        connected = summary.get('connectedNodeCount', 0)
        total = summary.get('totalNodeCount', 0)
        self.gauge('cluster.connected_node_count', connected, tags=base_tags)
        self.gauge('cluster.total_node_count', total, tags=base_tags)
        self.gauge('cluster.is_healthy', int(connected == total and total > 0), tags=base_tags)
