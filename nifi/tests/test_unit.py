# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# ABOUTME: Unit tests for the NiFi integration.
# ABOUTME: Tests API auth, health metrics, system diagnostics, and cluster health.
from unittest.mock import patch

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPConnectionError, HTTPStatusError
from datadog_checks.dev.http import MockHTTPResponse
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
    if json_data is not None:
        return MockHTTPResponse(status_code=status_code, json_data=json_data)
    return MockHTTPResponse(status_code=status_code, content=text)


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


EMPTY_BULLETIN_BOARD = {'bulletinBoard': {'bulletins': []}}

BULLETIN_BOARD_RESPONSE = {
    'bulletinBoard': {
        'bulletins': [
            {
                'id': 0,
                'groupId': 'pg-1',
                'sourceId': 'proc-1',
                'timestampIso': '2026-03-20T18:08:33.065Z',
                'canRead': True,
                'bulletin': {
                    'id': 0,
                    'sourceName': 'Fail Writer',
                    'level': 'ERROR',
                    'message': 'AccessDeniedException: /nonexistent',
                    'sourceType': 'PROCESSOR',
                    'timestampIso': '2026-03-20T18:08:33.065Z',
                },
            },
            {
                'id': 1,
                'groupId': 'pg-1',
                'sourceId': 'proc-1',
                'timestampIso': '2026-03-20T18:08:43.031Z',
                'canRead': True,
                'bulletin': {
                    'id': 1,
                    'sourceName': 'Fail Writer',
                    'level': 'WARNING',
                    'message': 'Disk space low',
                    'sourceType': 'PROCESSOR',
                    'timestampIso': '2026-03-20T18:08:43.031Z',
                },
            },
            {
                'id': 2,
                'groupId': 'pg-1',
                'sourceId': 'proc-2',
                'timestampIso': '2026-03-20T18:08:53.032Z',
                'canRead': False,
                'bulletin': {
                    'id': 2,
                    'sourceName': 'Secret Proc',
                    'level': 'ERROR',
                    'message': 'Should not see this',
                    'sourceType': 'PROCESSOR',
                },
            },
        ]
    }
}


def _standard_responses(
    cluster=CLUSTER_SUMMARY_STANDALONE, sysdiag=SYSTEM_DIAGNOSTICS_RESPONSE, bulletins=EMPTY_BULLETIN_BOARD
):
    """Return the standard URL->response mapping for a full check run."""
    return {
        '/access/token': _mock_response(201, text='test-token'),
        '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
        '/system-diagnostics': _mock_response(200, json_data=sysdiag),
        '/flow/status': _mock_response(200, json_data=FLOW_STATUS_RESPONSE),
        '/flow/process-groups/': _mock_response(200, json_data=PROCESS_GROUP_STATUS_RESPONSE),
        '/flow/cluster/summary': _mock_response(200, json_data=cluster),
        '/flow/bulletin-board': _mock_response(200, json_data=bulletins),
    }


def dispatch(responses_by_url):
    """Build a mock_http side_effect that dispatches by URL substring."""

    def side_effect(url, *args, **kwargs):
        for url_part, resp in responses_by_url.items():
            if url_part in url:
                return resp
        raise ValueError(f'Unmocked URL: {url}')

    return side_effect


def mock_http_responses(mock_http, responses_by_url):
    """Route mock_http GET and POST through a URL-substring dispatch."""
    mock_http.get.side_effect = dispatch(responses_by_url)
    mock_http.post.side_effect = dispatch(responses_by_url)


class TestAuth:
    def test_auth_success(self, mock_http):
        """Token endpoint returns 201 with raw JWT string."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        mock_http.post.return_value = _mock_response(201, text='jwt-token-string')
        api._authenticate()

        assert api._token == 'jwt-token-string'

    def test_auth_failure(self, mock_http):
        """Token endpoint returns 403 on bad credentials."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        mock_http.post.return_value = _mock_response(403)
        with pytest.raises(HTTPStatusError):
            api._authenticate()

    def test_token_refresh_on_401(self, mock_http):
        """First GET returns 401, re-auth succeeds, retry succeeds."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()
        api._token = 'expired-token'

        mock_http.get.side_effect = [
            _mock_response(401),
            _mock_response(200, json_data=ABOUT_RESPONSE),
        ]
        mock_http.post.return_value = _mock_response(201, text='new-token')

        result = api._request('/flow/about')

        assert result == ABOUT_RESPONSE
        assert api._token == 'new-token'


class TestCanConnect:
    def test_can_connect_success(self, dd_run_check, aggregator, mock_http):
        """Full check run emits can_connect=1 on success."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
        dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1, tags=['nifi_version:2.8.0'])

    def test_can_connect_failure(self, dd_run_check, aggregator, mock_http):
        """Connection error emits can_connect=0."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http.get.side_effect = HTTPConnectionError('refused')
        mock_http.post.side_effect = HTTPConnectionError('refused')
        with pytest.raises(Exception):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=0)

    def test_no_auth_mode(self, dd_run_check, aggregator, mock_http):
        """Check works without credentials when NiFi has no auth configured."""
        check = NifiCheck('nifi', {}, [_make_instance(username=None, password=None)])

        responses = {
            '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
            '/system-diagnostics': _mock_response(200, json_data=SYSTEM_DIAGNOSTICS_RESPONSE),
            '/flow/status': _mock_response(200, json_data=FLOW_STATUS_RESPONSE),
            '/flow/process-groups/': _mock_response(200, json_data=PROCESS_GROUP_STATUS_RESPONSE),
            '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE),
            '/flow/bulletin-board': _mock_response(200, json_data=EMPTY_BULLETIN_BOARD),
        }

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1, tags=['nifi_version:2.8.0'])


class TestClusterHealth:
    def test_cluster_healthy(self, dd_run_check, aggregator, mock_http):
        """Clustered mode with all nodes connected: is_healthy=1."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses(cluster=CLUSTER_SUMMARY_CLUSTERED))
        dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.connected_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.total_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.is_healthy', value=1, tags=tags)

    def test_cluster_degraded(self, dd_run_check, aggregator, mock_http):
        """Clustered mode with missing node: is_healthy=0."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses(cluster=CLUSTER_SUMMARY_DEGRADED))
        dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.is_healthy', value=0, tags=tags)

    def test_standalone_no_cluster_metrics(self, dd_run_check, aggregator, mock_http):
        """Standalone mode: no cluster metrics emitted."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
        dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1)
        assert not aggregator.metrics('nifi.cluster.connected_node_count')


class TestSystemDiagnostics:
    def test_jvm_metrics(self, dd_run_check, aggregator, mock_http):
        """System diagnostics emits JVM heap, threads, and CPU metrics."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
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

    def test_gc_metrics(self, dd_run_check, aggregator, mock_http):
        """GC metrics are tagged per garbage collector."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
        dd_run_check(check)

        young_tags = ['nifi_version:2.8.0', 'gc_name:G1 Young Generation']
        aggregator.assert_metric('nifi.system.gc.collection_count', value=12, tags=young_tags)
        aggregator.assert_metric('nifi.system.gc.collection_time', value=61, tags=young_tags)

        old_tags = ['nifi_version:2.8.0', 'gc_name:G1 Old Generation']
        aggregator.assert_metric('nifi.system.gc.collection_count', value=0, tags=old_tags)
        aggregator.assert_metric('nifi.system.gc.collection_time', value=0, tags=old_tags)

    def test_repository_metrics(self, dd_run_check, aggregator, mock_http):
        """Repository metrics include flowfile, content, and provenance repos."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
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

    def test_parse_utilization_unavailable(self):
        """N/A and None (returned by NiFi when metrics are unavailable) return 0.0."""
        assert NifiCheck._parse_utilization('N/A') == 0.0
        assert NifiCheck._parse_utilization(None) == 0.0
        assert NifiCheck._parse_utilization('') == 0.0


class TestFlowStatus:
    def test_flow_status_metrics(self, dd_run_check, aggregator, mock_http):
        """Controller-level flow status metrics are emitted."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
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
    def test_root_process_group(self, dd_run_check, aggregator, mock_http):
        """Root process group metrics are emitted with correct tags."""
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, _standard_responses())
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

    def test_nested_process_groups(self, dd_run_check, aggregator, mock_http):
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

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        root_tags = ['nifi_version:2.8.0', 'process_group_name:Root', 'process_group_id:root-id']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=10, tags=root_tags)

        child_tags = ['nifi_version:2.8.0', 'process_group_name:Child Group', 'process_group_id:child-id']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=5, tags=child_tags)
        aggregator.assert_metric('nifi.process_group.bytes_read', value=512, tags=child_tags)
        aggregator.assert_metric('nifi.process_group.active_threads', value=1, tags=child_tags)

    def test_overlapping_process_groups_no_duplicates(self, dd_run_check, aggregator, mock_http):
        """Configuring both a parent and child group ID does not emit duplicate metrics."""
        child_snapshot = {
            'id': 'child-id',
            'name': 'Child Group',
            'flowFilesQueued': 5,
            'bytesQueued': 0,
            'bytesRead': 0,
            'bytesWritten': 0,
            'flowFilesReceived': 0,
            'flowFilesSent': 0,
            'flowFilesTransferred': 0,
            'activeThreadCount': 1,
            'connectionStatusSnapshots': [],
            'processorStatusSnapshots': [],
            'processGroupStatusSnapshots': [],
        }
        parent_response = {
            'processGroupStatus': {
                'aggregateSnapshot': {
                    'id': 'root-id',
                    'name': 'Root',
                    'flowFilesQueued': 10,
                    'bytesQueued': 0,
                    'bytesRead': 0,
                    'bytesWritten': 0,
                    'flowFilesReceived': 0,
                    'flowFilesSent': 0,
                    'flowFilesTransferred': 0,
                    'activeThreadCount': 0,
                    'connectionStatusSnapshots': [],
                    'processorStatusSnapshots': [],
                    'processGroupStatusSnapshots': [{'processGroupStatusSnapshot': child_snapshot}],
                }
            }
        }
        child_response = {'processGroupStatus': {'aggregateSnapshot': child_snapshot}}

        responses = {
            '/access/token': _mock_response(201, text='test-token'),
            '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
            '/system-diagnostics': _mock_response(200, json_data=SYSTEM_DIAGNOSTICS_RESPONSE),
            '/flow/status': _mock_response(200, json_data=FLOW_STATUS_RESPONSE),
            'root-id': _mock_response(200, json_data=parent_response),
            'child-id': _mock_response(200, json_data=child_response),
            '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE),
            '/flow/bulletin-board': _mock_response(200, json_data=EMPTY_BULLETIN_BOARD),
        }
        mock_http_responses(mock_http, responses)

        check = NifiCheck('nifi', {}, [_make_instance(process_groups=['root-id', 'child-id'])])
        dd_run_check(check)

        child_tags = ['nifi_version:2.8.0', 'process_group_name:Child Group', 'process_group_id:child-id']
        # Child group should only appear once even though it's reachable via both root and direct listing
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=5, tags=child_tags, count=1)

    def test_missing_id_does_not_block_other_groups(self, dd_run_check, aggregator, mock_http):
        """Process groups with missing IDs are still emitted and don't block each other via visited set."""
        no_id_child_a = {
            'name': 'Child A',
            'flowFilesQueued': 10,
            'bytesQueued': 0,
            'bytesRead': 0,
            'bytesWritten': 0,
            'flowFilesReceived': 0,
            'flowFilesSent': 0,
            'flowFilesTransferred': 0,
            'activeThreadCount': 0,
            'connectionStatusSnapshots': [],
            'processorStatusSnapshots': [],
            'processGroupStatusSnapshots': [],
        }
        no_id_child_b = {
            'name': 'Child B',
            'flowFilesQueued': 20,
            'bytesQueued': 0,
            'bytesRead': 0,
            'bytesWritten': 0,
            'flowFilesReceived': 0,
            'flowFilesSent': 0,
            'flowFilesTransferred': 0,
            'activeThreadCount': 0,
            'connectionStatusSnapshots': [],
            'processorStatusSnapshots': [],
            'processGroupStatusSnapshots': [],
        }
        root_response = {
            'processGroupStatus': {
                'aggregateSnapshot': {
                    'id': 'root-id',
                    'name': 'Root',
                    'flowFilesQueued': 0,
                    'bytesQueued': 0,
                    'bytesRead': 0,
                    'bytesWritten': 0,
                    'flowFilesReceived': 0,
                    'flowFilesSent': 0,
                    'flowFilesTransferred': 0,
                    'activeThreadCount': 0,
                    'connectionStatusSnapshots': [],
                    'processorStatusSnapshots': [],
                    'processGroupStatusSnapshots': [
                        {'processGroupStatusSnapshot': no_id_child_a},
                        {'processGroupStatusSnapshot': no_id_child_b},
                    ],
                },
            }
        }
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=root_response)
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        # Both children should emit metrics even though neither has an 'id' field
        tags_a = ['nifi_version:2.8.0', 'process_group_name:Child A', 'process_group_id:unknown']
        tags_b = ['nifi_version:2.8.0', 'process_group_name:Child B', 'process_group_id:unknown']
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=10, tags=tags_a)
        aggregator.assert_metric('nifi.process_group.flowfiles_queued', value=20, tags=tags_b)


PG_WITH_CONNECTIONS_AND_PROCESSORS = {
    'processGroupStatus': {
        'id': 'root-pg-id',
        'name': 'NiFi Flow',
        'aggregateSnapshot': {
            'id': 'root-pg-id',
            'name': 'NiFi Flow',
            'flowFilesQueued': 0,
            'bytesQueued': 0,
            'bytesRead': 0,
            'bytesWritten': 0,
            'flowFilesReceived': 0,
            'flowFilesSent': 0,
            'flowFilesTransferred': 0,
            'activeThreadCount': 0,
            'processGroupStatusSnapshots': [],
            'connectionStatusSnapshots': [
                {
                    'id': 'conn-1',
                    'connectionStatusSnapshot': {
                        'id': 'conn-1',
                        'groupId': 'root-pg-id',
                        'name': 'success',
                        'sourceName': 'Generate Data',
                        'destinationName': 'Log Output',
                        'flowFilesQueued': 5,
                        'bytesQueued': 2048,
                        'percentUseCount': 10,
                        'percentUseBytes': 5,
                        'flowFilesIn': 10,
                        'flowFilesOut': 5,
                    },
                    'canRead': True,
                },
            ],
            'processorStatusSnapshots': [
                {
                    'id': 'proc-1',
                    'processorStatusSnapshot': {
                        'id': 'proc-1',
                        'groupId': 'root-pg-id',
                        'name': 'Generate Data',
                        'type': 'GenerateFlowFile',
                        'runStatus': 'Running',
                        'bytesRead': 0,
                        'bytesWritten': 1024,
                        'flowFilesIn': 0,
                        'flowFilesOut': 10,
                        'taskCount': 10,
                        'tasksDurationNanos': 5000000,
                        'activeThreadCount': 1,
                    },
                    'canRead': True,
                },
            ],
        },
    }
}


class TestConnectionMetrics:
    def test_disabled_by_default(self, dd_run_check, aggregator, mock_http):
        """Connection metrics are not emitted when collect_connection_metrics is false."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        assert not aggregator.metrics('nifi.connection.queued_count')

    def test_enabled(self, dd_run_check, aggregator, mock_http):
        """Connection metrics are emitted with correct tags when enabled."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance(collect_connection_metrics=True)])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        conn_tags = [
            'nifi_version:2.8.0',
            'connection_name:success',
            'source_name:Generate Data',
            'destination_name:Log Output',
            'process_group_id:root-pg-id',
        ]
        aggregator.assert_metric('nifi.connection.queued_count', value=5, tags=conn_tags)
        aggregator.assert_metric('nifi.connection.queued_bytes', value=2048, tags=conn_tags)
        aggregator.assert_metric('nifi.connection.percent_use_count', value=10, tags=conn_tags)
        aggregator.assert_metric('nifi.connection.percent_use_bytes', value=5, tags=conn_tags)
        aggregator.assert_metric('nifi.connection.flowfiles_in', value=10, tags=conn_tags)
        aggregator.assert_metric('nifi.connection.flowfiles_out', value=5, tags=conn_tags)

    def test_truncation_warning(self, dd_run_check, aggregator, mock_http, caplog):
        """Truncation warning is logged when connections exceed max_connections."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance(collect_connection_metrics=True, max_connections=0)])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        assert 'Truncated connections from 1 to 0' in caplog.text


class TestProcessorMetrics:
    def test_disabled_by_default(self, dd_run_check, aggregator, mock_http):
        """Processor metrics are not emitted when collect_processor_metrics is false."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance()])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        assert not aggregator.metrics('nifi.processor.flowfiles_in')

    def test_enabled(self, dd_run_check, aggregator, mock_http):
        """Processor metrics are emitted with correct tags when enabled."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance(collect_processor_metrics=True)])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        proc_tags = [
            'nifi_version:2.8.0',
            'processor_name:Generate Data',
            'processor_type:GenerateFlowFile',
            'process_group_id:root-pg-id',
        ]
        aggregator.assert_metric('nifi.processor.flowfiles_in', value=0, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.flowfiles_out', value=10, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.bytes_read', value=0, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.bytes_written', value=1024, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.task_count', value=10, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.processing_nanos', value=5000000, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.active_threads', value=1, tags=proc_tags)
        aggregator.assert_metric('nifi.processor.run_status', value=1, tags=proc_tags)

    def test_truncation_warning(self, dd_run_check, aggregator, mock_http, caplog):
        """Truncation warning is logged when processors exceed max_processors."""
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=PG_WITH_CONNECTIONS_AND_PROCESSORS)
        check = NifiCheck('nifi', {}, [_make_instance(collect_processor_metrics=True, max_processors=0)])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        assert 'Truncated processors from 1 to 0' in caplog.text

    @pytest.mark.parametrize(
        'run_status, expected_value',
        [
            ('Running', 1),
            ('Stopped', 0),
            ('Invalid', -1),
            ('Disabled', -2),
            ('Validating', -3),
            ('SomeFutureState', -1),
        ],
    )
    def test_run_status_mapping(self, dd_run_check, aggregator, mock_http, run_status, expected_value):
        """Each runStatus string maps to a distinct numeric value; unknown states map to -1."""
        pg_data = {
            'processGroupStatus': {
                'aggregateSnapshot': {
                    'id': 'root-pg-id',
                    'name': 'NiFi Flow',
                    'flowFilesQueued': 0,
                    'bytesQueued': 0,
                    'bytesRead': 0,
                    'bytesWritten': 0,
                    'flowFilesReceived': 0,
                    'flowFilesSent': 0,
                    'flowFilesTransferred': 0,
                    'activeThreadCount': 0,
                    'processGroupStatusSnapshots': [],
                    'connectionStatusSnapshots': [],
                    'processorStatusSnapshots': [
                        {
                            'processorStatusSnapshot': {
                                'id': 'proc-1',
                                'groupId': 'root-pg-id',
                                'name': 'TestProc',
                                'type': 'TestType',
                                'runStatus': run_status,
                                'bytesRead': 0,
                                'bytesWritten': 0,
                                'flowFilesIn': 0,
                                'flowFilesOut': 0,
                                'taskCount': 0,
                                'tasksDurationNanos': 0,
                                'activeThreadCount': 0,
                            },
                        },
                    ],
                },
            }
        }
        responses = _standard_responses()
        responses['/flow/process-groups/'] = _mock_response(200, json_data=pg_data)
        check = NifiCheck('nifi', {}, [_make_instance(collect_processor_metrics=True)])

        mock_http_responses(mock_http, responses)
        dd_run_check(check)

        proc_tags = [
            'nifi_version:2.8.0',
            'processor_name:TestProc',
            'processor_type:TestType',
            'process_group_id:root-pg-id',
        ]
        aggregator.assert_metric('nifi.processor.run_status', value=expected_value, tags=proc_tags)


class TestBulletins:
    @staticmethod
    def _run_bulletin_check(dd_run_check, mock_http, responses, cache_state='', **instance_overrides):
        """Run a check with mocked persistent cache for bulletin dedup isolation."""
        check = NifiCheck('nifi', {}, [_make_instance(**instance_overrides)])
        cache = {'last_bulletin_id': cache_state}

        mock_http_responses(mock_http, responses)
        with (
            patch.object(check, 'read_persistent_cache', side_effect=lambda k: cache.get(k, '')),
            patch.object(check, 'write_persistent_cache', side_effect=lambda k, v: cache.__setitem__(k, v)),
        ):
            dd_run_check(check)

        return check, cache

    def test_first_run_emits_events(self, dd_run_check, aggregator, mock_http):
        """First run with no cached ID emits all readable bulletins above min level."""
        responses = _standard_responses(bulletins=BULLETIN_BOARD_RESPONSE)
        _, cache = self._run_bulletin_check(dd_run_check, mock_http, responses)

        # Should emit 2 events: id=0 (ERROR, canRead=True) and id=1 (WARNING, canRead=True)
        # id=2 is skipped because canRead=False
        assert len(aggregator.events) == 2
        assert aggregator.events[0]['msg_title'] == 'NiFi Bulletin: Fail Writer [ERROR]'
        assert aggregator.events[0]['alert_type'] == 'error'
        assert aggregator.events[1]['msg_title'] == 'NiFi Bulletin: Fail Writer [WARNING]'
        assert aggregator.events[1]['alert_type'] == 'warning'

    def test_info_bulletin_alert_type(self, dd_run_check, aggregator, mock_http):
        """INFO bulletins get alert_type 'info', not 'warning'."""
        info_bulletins = {
            'bulletinBoard': {
                'bulletins': [
                    {
                        'id': 0,
                        'canRead': True,
                        'bulletin': {
                            'id': 0,
                            'sourceName': 'Info Source',
                            'level': 'INFO',
                            'message': 'Informational message',
                            'sourceType': 'PROCESSOR',
                        },
                    },
                ]
            }
        }
        responses = _standard_responses(bulletins=info_bulletins)
        _, cache = self._run_bulletin_check(dd_run_check, mock_http, responses, bulletin_min_level='INFO')
        assert len(aggregator.events) == 1
        assert aggregator.events[0]['alert_type'] == 'info'
        assert cache['last_bulletin_id'] == '0'

    def test_dedup_by_cached_id(self, dd_run_check, aggregator, mock_http):
        """Bulletins with id <= cached last_bulletin_id are skipped."""
        responses = _standard_responses(bulletins=BULLETIN_BOARD_RESPONSE)
        self._run_bulletin_check(dd_run_check, mock_http, responses, cache_state='0')

        # Only id=1 should be emitted (id=0 is <= cached, id=2 is unreadable)
        assert len(aggregator.events) == 1
        assert aggregator.events[0]['msg_title'] == 'NiFi Bulletin: Fail Writer [WARNING]'

    def test_min_level_filtering(self, dd_run_check, aggregator, mock_http):
        """Bulletins below min level are filtered out."""
        responses = _standard_responses(bulletins=BULLETIN_BOARD_RESPONSE)
        self._run_bulletin_check(dd_run_check, mock_http, responses, bulletin_min_level='ERROR')

        # Only id=0 (ERROR) should be emitted; id=1 (WARNING) is below ERROR level
        assert len(aggregator.events) == 1
        assert aggregator.events[0]['alert_type'] == 'error'

    def test_empty_bulletin_board(self, dd_run_check, aggregator, mock_http):
        """No events emitted when bulletin board is empty."""
        self._run_bulletin_check(dd_run_check, mock_http, _standard_responses())
        assert len(aggregator.events) == 0

    def test_bulletins_disabled(self, dd_run_check, aggregator, mock_http):
        """No bulletin collection when collect_bulletins is false."""
        responses = _standard_responses(bulletins=BULLETIN_BOARD_RESPONSE)
        self._run_bulletin_check(dd_run_check, mock_http, responses, collect_bulletins=False)
        assert len(aggregator.events) == 0

    def test_max_bulletins_per_cycle(self, dd_run_check, aggregator, mock_http):
        """Only max_bulletins_per_cycle events are emitted."""
        responses = _standard_responses(bulletins=BULLETIN_BOARD_RESPONSE)
        self._run_bulletin_check(dd_run_check, mock_http, responses, max_bulletins_per_cycle=1)
        assert len(aggregator.events) == 1

    def test_id_reset_after_nifi_restart(self, dd_run_check, aggregator, mock_http):
        """Bulletin IDs reset to 0 on NiFi restart; cached high-water mark must be cleared."""
        post_restart_bulletins = {
            'bulletinBoard': {
                'bulletins': [
                    {
                        'id': 0,
                        'canRead': True,
                        'bulletin': {
                            'id': 0,
                            'sourceName': 'Post-Restart Proc',
                            'level': 'ERROR',
                            'message': 'Post-restart error',
                            'sourceType': 'PROCESSOR',
                        },
                    },
                ]
            }
        }
        responses = _standard_responses(bulletins=post_restart_bulletins)
        # Cached last_id=500 simulates a pre-restart high-water mark.
        # New bulletin id=0 should still be emitted after reset detection.
        _, cache = self._run_bulletin_check(dd_run_check, mock_http, responses, cache_state='500')

        assert len(aggregator.events) == 1
        assert aggregator.events[0]['msg_title'] == 'NiFi Bulletin: Post-Restart Proc [ERROR]'
        assert cache['last_bulletin_id'] == '0'
