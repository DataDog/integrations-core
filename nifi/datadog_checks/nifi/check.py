# ABOUTME: Datadog Agent check for Apache NiFi.
# ABOUTME: Polls the NiFi REST API to collect JVM, flow, queue, processor, and bulletin data.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

from .api import NiFiApi


class NifiCheck(AgentCheck):
    __NAMESPACE__ = 'nifi'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
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
            gc_tags = base_tags + [f'gc_name:{gc["name"]}']
            self.monotonic_count('system.gc.collection_count', gc.get('collectionCount', 0), tags=gc_tags)
            self.monotonic_count('system.gc.collection_time', gc.get('collectionMillis', 0), tags=gc_tags)

        ff_repo = snap.get('flowFileRepositoryStorageUsage', {})
        self.gauge('system.flowfile_repo.used_space', ff_repo.get('usedSpaceBytes', 0), tags=base_tags)
        self.gauge('system.flowfile_repo.free_space', ff_repo.get('freeSpaceBytes', 0), tags=base_tags)
        ff_util = ff_repo.get('utilization', '0%')
        self.gauge('system.flowfile_repo.utilization', self._parse_utilization(ff_util), tags=base_tags)

        for repo in snap.get('contentRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo["identifier"]}']
            self.gauge('system.content_repo.used_space', repo.get('usedSpaceBytes', 0), tags=repo_tags)
            self.gauge('system.content_repo.free_space', repo.get('freeSpaceBytes', 0), tags=repo_tags)
            repo_util = repo.get('utilization', '0%')
            self.gauge('system.content_repo.utilization', self._parse_utilization(repo_util), tags=repo_tags)

        for repo in snap.get('provenanceRepositoryStorageUsage', []):
            repo_tags = base_tags + [f'repo_identifier:{repo["identifier"]}']
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
            data = api.get_process_group_status(pg_id)
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

        for child in snap.get('processGroupStatusSnapshots', []):
            child_status = child.get('processGroupStatusSnapshot', {})
            if child_status:
                self._emit_process_group({'aggregateSnapshot': child_status}, base_tags)

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
