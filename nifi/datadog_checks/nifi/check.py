# ABOUTME: Datadog Agent check for Apache NiFi.
# ABOUTME: Polls the NiFi REST API to collect JVM, flow, queue, processor, and bulletin data.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timezone

from datadog_checks.base import AgentCheck

from .api import NiFiApi
from .constants import BULLETIN_LEVEL_ORDER


class NifiCheck(AgentCheck):
    __NAMESPACE__ = 'nifi'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # NiFi uses its own token-based auth (POST /access/token), not HTTP Basic Auth.
        # Disable only the automatic Basic Auth that RequestsWrapper adds from username/password.
        # Preserve any explicitly configured auth (digest, kerberos, ntlm) for proxy scenarios.
        auth = self.http.options.get('auth')
        if auth is not None and type(auth) is tuple:
            self.http.options['auth'] = None
        self._api = None

    def _get_api(self):
        if self._api is None:
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

            self.gauge('can_connect', 1, tags=base_tags)
        except Exception:
            self.log.exception('NiFi check failed')
            self.gauge('can_connect', 0, tags=self.instance.get('tags', []))
            raise

    @staticmethod
    def _parse_utilization(value):
        """Parse a percentage string like '16.0%' to a float."""
        if isinstance(value, str) and value.endswith('%'):
            return float(value.rstrip('%'))
        return float(value)

    def _collect_system_diagnostics(self, api, base_tags):
        data = api.get_system_diagnostics()
        snap = data.get('systemDiagnostics', {}).get('aggregateSnapshot', {})

        self.gauge('system.jvm.heap_used', snap.get('usedHeapBytes', 0), tags=base_tags)
        self.gauge('system.jvm.heap_max', snap.get('maxHeapBytes', 0), tags=base_tags)
        heap_util = snap.get('heapUtilization', '0%')
        self.gauge('system.jvm.heap_utilization', self._parse_utilization(heap_util), tags=base_tags)
        self.gauge('system.jvm.non_heap_used', snap.get('usedNonHeapBytes', 0), tags=base_tags)
        self.gauge('system.jvm.total_threads', snap.get('totalThreads', 0), tags=base_tags)
        self.gauge('system.jvm.daemon_threads', snap.get('daemonThreads', 0), tags=base_tags)
        self.gauge('system.cpu.load_average', snap.get('processorLoadAverage', 0), tags=base_tags)
        self.gauge('system.cpu.available_processors', snap.get('availableProcessors', 0), tags=base_tags)

        for gc in snap.get('garbageCollection', []):
            gc_tags = base_tags + [f'gc_name:{gc.get("name", "unknown")}']
            self.monotonic_count('system.gc.collection_count', gc.get('collectionCount', 0), tags=gc_tags)
            self.monotonic_count('system.gc.collection_time', gc.get('collectionMillis', 0), tags=gc_tags)

        ff_repo = snap.get('flowFileRepositoryStorageUsage', {})
        self.gauge('system.flowfile_repo.used_space', ff_repo.get('usedSpaceBytes', 0), tags=base_tags)
        self.gauge('system.flowfile_repo.free_space', ff_repo.get('freeSpaceBytes', 0), tags=base_tags)
        ff_util = ff_repo.get('utilization', '0%')
        self.gauge('system.flowfile_repo.utilization', self._parse_utilization(ff_util), tags=base_tags)

        for repo in snap.get('contentRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo.get("identifier", "unknown")}']
            self.gauge('system.content_repo.used_space', repo.get('usedSpaceBytes', 0), tags=repo_tags)
            self.gauge('system.content_repo.free_space', repo.get('freeSpaceBytes', 0), tags=repo_tags)
            repo_util = repo.get('utilization', '0%')
            self.gauge('system.content_repo.utilization', self._parse_utilization(repo_util), tags=repo_tags)

        for repo in snap.get('provenanceRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo.get("identifier", "unknown")}']
            self.gauge('system.provenance_repo.used_space', repo.get('usedSpaceBytes', 0), tags=repo_tags)
            self.gauge('system.provenance_repo.free_space', repo.get('freeSpaceBytes', 0), tags=repo_tags)
            repo_util = repo.get('utilization', '0%')
            self.gauge('system.provenance_repo.utilization', self._parse_utilization(repo_util), tags=repo_tags)

    def _collect_flow_status(self, api, base_tags):
        data = api.get_flow_status()
        status = data.get('controllerStatus', {})

        self.gauge('flow.active_threads', status.get('activeThreadCount', 0), tags=base_tags)
        self.gauge('flow.flowfiles_queued', status.get('flowFilesQueued', 0), tags=base_tags)
        self.gauge('flow.bytes_queued', status.get('bytesQueued', 0), tags=base_tags)
        self.gauge('flow.running_count', status.get('runningCount', 0), tags=base_tags)
        self.gauge('flow.stopped_count', status.get('stoppedCount', 0), tags=base_tags)
        self.gauge('flow.invalid_count', status.get('invalidCount', 0), tags=base_tags)
        self.gauge('flow.disabled_count', status.get('disabledCount', 0), tags=base_tags)

    def _collect_process_group_metrics(self, api, base_tags):
        process_groups = self.instance.get('process_groups', ['root'])
        for pg_id in process_groups:
            try:
                data = api.get_process_group_status(pg_id)
            except Exception:
                self.log.warning('Failed to collect metrics for process group %s', pg_id, exc_info=True)
                continue
            pg_status = data.get('processGroupStatus', {})
            self._emit_process_group(pg_status, base_tags)

    def _emit_process_group(self, pg_status, base_tags):
        """Emit metrics for a process group and recurse into child groups."""
        snap = pg_status.get('aggregateSnapshot', {})
        pg_tags = base_tags + [
            f'process_group_name:{snap.get("name", "unknown")}',
            f'process_group_id:{snap.get("id", "unknown")}',
        ]

        self.gauge('process_group.flowfiles_queued', snap.get('flowFilesQueued', 0), tags=pg_tags)
        self.gauge('process_group.bytes_queued', snap.get('bytesQueued', 0), tags=pg_tags)
        self.gauge('process_group.bytes_read', snap.get('bytesRead', 0), tags=pg_tags)
        self.gauge('process_group.bytes_written', snap.get('bytesWritten', 0), tags=pg_tags)
        self.gauge('process_group.flowfiles_received', snap.get('flowFilesReceived', 0), tags=pg_tags)
        self.gauge('process_group.flowfiles_sent', snap.get('flowFilesSent', 0), tags=pg_tags)
        self.gauge('process_group.flowfiles_transferred', snap.get('flowFilesTransferred', 0), tags=pg_tags)
        self.gauge('process_group.active_threads', snap.get('activeThreadCount', 0), tags=pg_tags)

        if self.instance.get('collect_connection_metrics', False):
            self._emit_connection_metrics(snap, base_tags)

        if self.instance.get('collect_processor_metrics', False):
            self._emit_processor_metrics(snap, base_tags)

        for child in snap.get('processGroupStatusSnapshots', []):
            child_status = child.get('processGroupStatusSnapshot', {})
            if child_status:
                self._emit_process_group({'aggregateSnapshot': child_status}, base_tags)

    def _emit_connection_metrics(self, pg_snap, base_tags):
        max_connections = self.instance.get('max_connections', 200)
        all_connections = pg_snap.get('connectionStatusSnapshots', [])
        connections = sorted(
            all_connections,
            key=lambda c: c.get('connectionStatusSnapshot', {}).get('flowFilesQueued', 0),
            reverse=True,
        )[:max_connections]

        if len(all_connections) > max_connections:
            self.log.warning(
                'Process group %s: truncated connections from %d to %d (max_connections)',
                pg_snap.get('name', 'unknown'),
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
            self.gauge('connection.queued_count', snap.get('flowFilesQueued', 0), tags=conn_tags)
            self.gauge('connection.queued_bytes', snap.get('bytesQueued', 0), tags=conn_tags)
            self.gauge('connection.percent_use_count', snap.get('percentUseCount', 0), tags=conn_tags)
            self.gauge('connection.percent_use_bytes', snap.get('percentUseBytes', 0), tags=conn_tags)
            self.gauge('connection.flowfiles_in', snap.get('flowFilesIn', 0), tags=conn_tags)
            self.gauge('connection.flowfiles_out', snap.get('flowFilesOut', 0), tags=conn_tags)

    RUN_STATUS_MAP = {'Running': 1, 'Stopped': 0, 'Validating': 0, 'Invalid': -1, 'Disabled': -2}

    def _emit_processor_metrics(self, pg_snap, base_tags):
        max_processors = self.instance.get('max_processors', 200)
        all_processors = pg_snap.get('processorStatusSnapshots', [])
        processors = sorted(
            all_processors,
            key=lambda p: p.get('processorStatusSnapshot', {}).get('taskCount', 0),
            reverse=True,
        )[:max_processors]

        if len(all_processors) > max_processors:
            self.log.warning(
                'Process group %s: truncated processors from %d to %d (max_processors)',
                pg_snap.get('name', 'unknown'),
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
            self.gauge('processor.flowfiles_in', snap.get('flowFilesIn', 0), tags=proc_tags)
            self.gauge('processor.flowfiles_out', snap.get('flowFilesOut', 0), tags=proc_tags)
            self.gauge('processor.bytes_read', snap.get('bytesRead', 0), tags=proc_tags)
            self.gauge('processor.bytes_written', snap.get('bytesWritten', 0), tags=proc_tags)
            self.gauge('processor.task_count', snap.get('taskCount', 0), tags=proc_tags)
            self.gauge('processor.processing_nanos', snap.get('tasksDurationNanos', 0), tags=proc_tags)
            self.gauge('processor.active_threads', snap.get('activeThreadCount', 0), tags=proc_tags)
            run_status = self.RUN_STATUS_MAP.get(snap.get('runStatus', ''), -1)
            self.gauge('processor.run_status', run_status, tags=proc_tags)

    _CACHE_KEY_LAST_BULLETIN_ID = 'last_bulletin_id'

    def _collect_bulletins(self, api, base_tags):
        data = api.get_bulletin_board()
        bulletins = data.get('bulletinBoard', {}).get('bulletins', [])

        last_id_str = self.read_persistent_cache(self._CACHE_KEY_LAST_BULLETIN_ID)
        last_id = int(last_id_str) if last_id_str else -1

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
                    ts = int(dt.replace(tzinfo=timezone.utc if dt.tzinfo is None else dt.tzinfo).timestamp())
                except (ValueError, OSError):
                    pass

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
                    'alert_type': 'error' if level == 'ERROR' else 'warning' if level == 'WARNING' else 'info',
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
