# ABOUTME: Unit tests for the NiFi integration.
# ABOUTME: Tests API auth, health metrics, system diagnostics, and cluster health.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError

from datadog_checks.nifi import NifiCheck


def _make_instance(**overrides):
    instance = {
        'api_url': 'https://nifi.example.com:8443/nifi-api',
        'username': 'admin',
        'password': 'secret',
        'tls_verify': False,
    }
    instance.update(overrides)
    return instance


def _mock_response(status_code=200, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = {}
    resp.content = b'content'
    if status_code >= 400:
        resp.raise_for_status.side_effect = HTTPError(f'{status_code}')
    else:
        resp.raise_for_status.return_value = None
    return resp


ABOUT_RESPONSE = {'about': {'title': 'NiFi', 'version': '2.8.0'}}

CLUSTER_SUMMARY_STANDALONE = {'clusterSummary': {'clustered': False, 'connectedNodeCount': 0, 'totalNodeCount': 0}}

CLUSTER_SUMMARY_CLUSTERED = {
    'clusterSummary': {'clustered': True, 'connectedNodeCount': 3, 'totalNodeCount': 3, 'connectedToCluster': True}
}

CLUSTER_SUMMARY_DEGRADED = {
    'clusterSummary': {'clustered': True, 'connectedNodeCount': 2, 'totalNodeCount': 3, 'connectedToCluster': True}
}

SYSTEM_DIAGNOSTICS_RESPONSE = {
    'systemDiagnostics': {
        'aggregateSnapshot': {
            'usedHeapBytes': 217252040,
            'maxHeapBytes': 1073741824,
            'heapUtilization': '20.0%',
            'usedNonHeapBytes': 172266584,
            'totalThreads': 88,
            'daemonThreads': 44,
            'availableProcessors': 16,
            'processorLoadAverage': 1.73,
            'garbageCollection': [
                {'name': 'G1 Young Generation', 'collectionCount': 12, 'collectionMillis': 61},
                {'name': 'G1 Old Generation', 'collectionCount': 0, 'collectionMillis': 0},
            ],
            'flowFileRepositoryStorageUsage': {
                'usedSpaceBytes': 86076280832,
                'freeSpaceBytes': 891819843584,
                'utilization': '9.0%',
            },
            'contentRepositoryStorageUsage': [
                {
                    'identifier': 'default',
                    'usedSpaceBytes': 86076280832,
                    'freeSpaceBytes': 891819843584,
                    'utilization': '9.0%',
                }
            ],
            'provenanceRepositoryStorageUsage': [
                {
                    'identifier': 'default',
                    'usedSpaceBytes': 86076280832,
                    'freeSpaceBytes': 891819843584,
                    'utilization': '9.0%',
                }
            ],
        }
    }
}


FLOW_STATUS_RESPONSE = {
    'controllerStatus': {
        'activeThreadCount': 2,
        'flowFilesQueued': 10,
        'bytesQueued': 5120,
        'runningCount': 4,
        'stoppedCount': 0,
        'invalidCount': 0,
        'disabledCount': 1,
    }
}

PROCESS_GROUP_STATUS_RESPONSE = {
    'processGroupStatus': {
        'id': 'root-pg-id',
        'name': 'NiFi Flow',
        'aggregateSnapshot': {
            'id': 'root-pg-id',
            'name': 'NiFi Flow',
            'flowFilesQueued': 10,
            'bytesQueued': 5120,
            'bytesRead': 1024,
            'bytesWritten': 2048,
            'flowFilesReceived': 5,
            'flowFilesSent': 3,
            'flowFilesTransferred': 8,
            'activeThreadCount': 2,
            'connectionStatusSnapshots': [],
            'processorStatusSnapshots': [],
            'processGroupStatusSnapshots': [],
        },
    }
}


def _standard_responses(cluster=CLUSTER_SUMMARY_STANDALONE, sysdiag=SYSTEM_DIAGNOSTICS_RESPONSE):
    """Return the standard URL->response mapping for a full check run."""
    return {
        '/access/token': _mock_response(201, text='test-token'),
        '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
        '/system-diagnostics': _mock_response(200, json_data=sysdiag),
        '/flow/status': _mock_response(200, json_data=FLOW_STATUS_RESPONSE),
        '/flow/process-groups/': _mock_response(200, json_data=PROCESS_GROUP_STATUS_RESPONSE),
        '/flow/cluster/summary': _mock_response(200, json_data=cluster),
    }


def _build_request_side_effect(responses_by_url):
    """Build a side_effect for requests.Session.request that dispatches by URL substring."""

    def side_effect(method, url, **kwargs):
        for url_part, resp in responses_by_url.items():
            if url_part in url:
                return resp
        raise ValueError(f'Unmocked URL: {method} {url}')

    return side_effect


class TestAuth:
    def test_auth_success(self):
        """Token endpoint returns 201 with raw JWT string."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        with patch('requests.Session.request', return_value=_mock_response(201, text='jwt-token-string')):
            api._authenticate()

        assert api._token == 'jwt-token-string'

    def test_auth_failure(self):
        """Token endpoint returns 403 on bad credentials."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        with patch('requests.Session.request', return_value=_mock_response(403)):
            with pytest.raises(HTTPError):
                api._authenticate()

    def test_token_refresh_on_401(self):
        """First GET returns 401, re-auth succeeds, retry succeeds."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()
        api._token = 'expired-token'

        responses = iter(
            [
                _mock_response(401),
                _mock_response(201, text='new-token'),
                _mock_response(200, json_data=ABOUT_RESPONSE),
            ]
        )

        with patch('requests.Session.request', side_effect=lambda *a, **kw: next(responses)):
            result = api._request('/flow/about')

        assert result == ABOUT_RESPONSE
        assert api._token == 'new-token'


class TestCanConnect:
    def test_can_connect_success(self, dd_run_check, aggregator):
        """Full check run emits can_connect=1 on success."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1, tags=['nifi_version:2.8.0'])

    def test_can_connect_failure(self, dd_run_check, aggregator):
        """Connection error emits can_connect=0."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=RequestsConnectionError('refused')):
            with pytest.raises(Exception):
                dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=0)

    def test_no_auth_mode(self, dd_run_check, aggregator):
        """Check works without credentials when NiFi has no auth configured."""
        check = NifiCheck('nifi', {}, [_make_instance(username=None, password=None)])

        responses = {
            '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
            '/system-diagnostics': _mock_response(200, json_data=SYSTEM_DIAGNOSTICS_RESPONSE),
            '/flow/status': _mock_response(200, json_data=FLOW_STATUS_RESPONSE),
            '/flow/process-groups/': _mock_response(200, json_data=PROCESS_GROUP_STATUS_RESPONSE),
            '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE),
        }

        with patch('requests.Session.request', side_effect=_build_request_side_effect(responses)):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1, tags=['nifi_version:2.8.0'])


class TestClusterHealth:
    def test_cluster_healthy(self, dd_run_check, aggregator):
        """Clustered mode with all nodes connected: is_healthy=1."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch(
            'requests.Session.request',
            side_effect=_build_request_side_effect(_standard_responses(cluster=CLUSTER_SUMMARY_CLUSTERED)),
        ):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.connected_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.total_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.is_healthy', value=1, tags=tags)

    def test_cluster_degraded(self, dd_run_check, aggregator):
        """Clustered mode with missing node: is_healthy=0."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch(
            'requests.Session.request',
            side_effect=_build_request_side_effect(_standard_responses(cluster=CLUSTER_SUMMARY_DEGRADED)),
        ):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.is_healthy', value=0, tags=tags)

    def test_standalone_no_cluster_metrics(self, dd_run_check, aggregator):
        """Standalone mode: no cluster metrics emitted."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1)
        assert not aggregator.metrics('nifi.cluster.connected_node_count')


class TestSystemDiagnostics:
    def test_jvm_metrics(self, dd_run_check, aggregator):
        """System diagnostics emits JVM heap, threads, and CPU metrics."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.system.jvm.heap_used', value=217252040, tags=tags)
        aggregator.assert_metric('nifi.system.jvm.heap_max', value=1073741824, tags=tags)
        aggregator.assert_metric('nifi.system.jvm.heap_utilization', value=20.0, tags=tags)
        aggregator.assert_metric('nifi.system.jvm.non_heap_used', value=172266584, tags=tags)
        aggregator.assert_metric('nifi.system.jvm.total_threads', value=88, tags=tags)
        aggregator.assert_metric('nifi.system.jvm.daemon_threads', value=44, tags=tags)
        aggregator.assert_metric('nifi.system.cpu.load_average', value=1.73, tags=tags)
        aggregator.assert_metric('nifi.system.cpu.available_processors', value=16, tags=tags)

    def test_gc_metrics(self, dd_run_check, aggregator):
        """GC metrics are tagged per garbage collector."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        young_tags = ['nifi_version:2.8.0', 'gc_name:G1 Young Generation']
        aggregator.assert_metric('nifi.system.gc.collection_count', value=12, tags=young_tags)
        aggregator.assert_metric('nifi.system.gc.collection_time', value=61, tags=young_tags)

        old_tags = ['nifi_version:2.8.0', 'gc_name:G1 Old Generation']
        aggregator.assert_metric('nifi.system.gc.collection_count', value=0, tags=old_tags)
        aggregator.assert_metric('nifi.system.gc.collection_time', value=0, tags=old_tags)

    def test_repository_metrics(self, dd_run_check, aggregator):
        """Repository metrics include flowfile, content, and provenance repos."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.system.flowfile_repo.used_space', value=86076280832, tags=tags)
        aggregator.assert_metric('nifi.system.flowfile_repo.free_space', value=891819843584, tags=tags)
        aggregator.assert_metric('nifi.system.flowfile_repo.utilization', value=9.0, tags=tags)

        repo_tags = tags + ['repo_identifier:default']
        aggregator.assert_metric('nifi.system.content_repo.used_space', value=86076280832, tags=repo_tags)
        aggregator.assert_metric('nifi.system.content_repo.utilization', value=9.0, tags=repo_tags)
        aggregator.assert_metric('nifi.system.provenance_repo.used_space', value=86076280832, tags=repo_tags)
        aggregator.assert_metric('nifi.system.provenance_repo.utilization', value=9.0, tags=repo_tags)

    def test_parse_utilization(self):
        """Percentage strings are parsed correctly."""
        assert NifiCheck._parse_utilization('16.0%') == 16.0
        assert NifiCheck._parse_utilization('0%') == 0.0
        assert NifiCheck._parse_utilization('100.0%') == 100.0
        assert NifiCheck._parse_utilization(42.5) == 42.5


class TestFlowStatus:
    def test_flow_status_metrics(self, dd_run_check, aggregator):
        """Controller-level flow status metrics are emitted."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.flow.active_threads', value=2, tags=tags)
        aggregator.assert_metric('nifi.flow.flowfiles_queued', value=10, tags=tags)
        aggregator.assert_metric('nifi.flow.bytes_queued', value=5120, tags=tags)
        aggregator.assert_metric('nifi.flow.running_count', value=4, tags=tags)
        aggregator.assert_metric('nifi.flow.stopped_count', value=0, tags=tags)
        aggregator.assert_metric('nifi.flow.invalid_count', value=0, tags=tags)
        aggregator.assert_metric('nifi.flow.disabled_count', value=1, tags=tags)


class TestProcessGroup:
    def test_root_process_group(self, dd_run_check, aggregator):
        """Root process group metrics are emitted with correct tags."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(_standard_responses())):
            dd_run_check(check)

        pg_tags = ['nifi_version:2.8.0', 'process_group_name:NiFi Flow', 'process_group_id:root-pg-id']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=10, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.bytes_queued', value=5120, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.bytes_read', value=1024, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.bytes_written', value=2048, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.flowfiles_received', value=5, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.flowfiles_sent', value=3, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.flowfiles_transferred', value=8, tags=pg_tags)
        aggregator.assert_metric('nifi.process_group.active_threads', value=2, tags=pg_tags)

    def test_nested_process_groups(self, dd_run_check, aggregator):
        """Nested process groups are recursively flattened."""
        nested_response = {
            'processGroupStatus': {
                'id': 'root-id',
                'name': 'Root',
                'aggregateSnapshot': {
                    'id': 'root-id',
                    'name': 'Root',
                    'flowFilesQueued': 10,
                    'bytesQueued': 5120,
                    'bytesRead': 0,
                    'bytesWritten': 0,
                    'flowFilesReceived': 0,
                    'flowFilesSent': 0,
                    'flowFilesTransferred': 0,
                    'activeThreadCount': 0,
                    'connectionStatusSnapshots': [],
                    'processorStatusSnapshots': [],
                    'processGroupStatusSnapshots': [
                        {
                            'id': 'child-id',
                            'processGroupStatusSnapshot': {
                                'id': 'child-id',
                                'name': 'Child Group',
                                'flowFilesQueued': 5,
                                'bytesQueued': 2048,
                                'bytesRead': 512,
                                'bytesWritten': 256,
                                'flowFilesReceived': 2,
                                'flowFilesSent': 1,
                                'flowFilesTransferred': 3,
                                'activeThreadCount': 1,
                                'connectionStatusSnapshots': [],
                                'processorStatusSnapshots': [],
                                'processGroupStatusSnapshots': [],
                            },
                        }
                    ],
                },
            }
        }

        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=nested_response)
        check = NifiCheck('nifi', {}, [_make_instance()])

        with patch('requests.Session.request', side_effect=_build_request_side_effect(responses)):
            dd_run_check(check)

        root_tags = ['nifi_version:2.8.0', 'process_group_name:Root', 'process_group_id:root-id']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=10, tags=root_tags)

        child_tags = ['nifi_version:2.8.0', 'process_group_name:Child Group', 'process_group_id:child-id']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=5, tags=child_tags)
        aggregator.assert_metric('nifi.process_group.bytes_read', value=512, tags=child_tags)
        aggregator.assert_metric('nifi.process_group.active_threads', value=1, tags=child_tags)
