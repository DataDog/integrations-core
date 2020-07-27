# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.marklogic.parsers.common import MarkLogicParserException, build_metric_to_submit
from datadog_checks.marklogic.parsers.health import parse_summary_health
from datadog_checks.marklogic.parsers.request import parse_summary_request_resource_metrics
from datadog_checks.marklogic.parsers.status import (
    parse_summary_status_base_metrics,
    parse_summary_status_resource_metrics,
)
from datadog_checks.marklogic.parsers.storage import parse_summary_storage_base_metrics

from .common import read_fixture_file


def test_build_metric_to_submit():
    # type: () -> None
    # Simple int gauge metric
    assert build_metric_to_submit('forests.stuff', 33, ['tést:tèst']) == ('gauge', 'forests.stuff', 33, ['tést:tèst'])

    # Gauge with units
    assert build_metric_to_submit('forests.stuff', {'units': 'MB/sec', 'value': 42.2}) == (
        'gauge',
        'forests.stuff',
        42.2,
        None,
    )

    # Unkonwn unit
    assert build_metric_to_submit('forests.stuff', {'units': 'unknown', 'value': 42.2}) is None

    with pytest.raises(MarkLogicParserException):
        build_metric_to_submit('forests.stuff', {'unknown': 3})


def test_parse_summary_storage_base_metrics():
    # type: () -> None
    forests_storage_data = read_fixture_file('storage/forests_storage.yaml')

    EXPECTED_RESULT = [
        (
            'gauge',
            'forests.storage.host.capacity',
            '98.25175',
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
        (
            'gauge',
            'forests.storage.host.device-space',
            1134,
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
        (
            'gauge',
            'forests.storage.host.forest-reserve',
            20,
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
        (
            'gauge',
            'forests.storage.host.forest-size',
            10,
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
        (
            'gauge',
            'forests.storage.host.large-data-size',
            0,
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            8,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:9587943635595974971',
                'forest_name:App-Services',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:16432829063228140680',
                'forest_name:Documents',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:1734136458884541932',
                'forest_name:Extensions',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:17357483631506654578',
                'forest_name:Fab',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:3674269176556456706',
                'forest_name:Last-Login',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            1,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:10607054817847962887',
                'forest_name:Meters',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:9575981178809949288',
                'forest_name:Modules',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:868218461567003688',
                'forest_name:Schemas',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            1,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:5279551105645884758',
                'forest_name:Security',
            ],
        ),
        (
            'gauge',
            'forests.storage.forest.disk-size',
            0,
            [
                'foo:bar',
                'host_id:9614261020922107465',
                'host_name:26f962ec5443',
                'storage_path:/var/opt/MarkLogic',
                'forest_id:15616040811356121157',
                'forest_name:Triggers',
            ],
        ),
        (
            'gauge',
            'forests.storage.host.remaining-space',
            1114,
            ['foo:bar', 'host_id:9614261020922107465', 'host_name:26f962ec5443', 'storage_path:/var/opt/MarkLogic'],
        ),
    ]

    result = list(parse_summary_storage_base_metrics(forests_storage_data, ['foo:bar']))

    assert sorted(result) == sorted(EXPECTED_RESULT)


def test_parse_summary_status_base_metrics():
    # type: () -> None
    status_base_data = read_fixture_file('status/base_status.yaml')

    EXPECTED_RESULT = [
        # # TODO: ignore forests-status-summary (duplicated)
        # ('gauge', 'forests.backup-count', 0, ['foo:bar']),
        # ('gauge', 'forests.max-stands-per-forest', 1, ['foo:bar']),
        # ('gauge', 'forests.merge-count', 0, ['foo:bar']),
        # ('gauge', 'forests.restore-count', 0, ['foo:bar']),
        # ('gauge', 'forests.state-not-open', 0, ['foo:bar']),
        # ('gauge', 'forests.total-forests', 10, ['foo:bar']),
        # # TODO: ignore hosts-status-summary (duplicated)
        ('gauge', 'hosts.total-load', 0, ['foo:bar']),
        ('gauge', 'hosts.backup-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.backup-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.deadlock-wait-load', 0, ['foo:bar']),
        ('gauge', 'hosts.external-binary-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-client-receive-load', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-client-send-load', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-server-receive-load', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-server-send-load', 0, ['foo:bar']),
        ('gauge', 'hosts.journal-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.large-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.large-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.merge-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.merge-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.query-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.read-lock-hold-load', 0, ['foo:bar']),
        ('gauge', 'hosts.read-lock-wait-load', 0, ['foo:bar']),
        ('gauge', 'hosts.restore-read-load', 0, ['foo:bar']),
        ('gauge', 'hosts.restore-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.save-write-load', 0, ['foo:bar']),
        ('gauge', 'hosts.write-lock-hold-load', 0, ['foo:bar']),
        ('gauge', 'hosts.write-lock-wait-load', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-client-receive-load', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-client-send-load', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-server-receive-load', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-server-send-load', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-process-huge-pages-size', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-process-rss', 449, ['foo:bar']),
        ('gauge', 'hosts.memory-size', 6144, ['foo:bar']),
        ('gauge', 'hosts.memory-system-free', 5525, ['foo:bar']),
        ('gauge', 'hosts.memory-system-total', 5947, ['foo:bar']),
        ('gauge', 'hosts.total-rate', 16.639799118042, ['foo:bar']),
        ('gauge', 'hosts.backup-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.backup-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.deadlock-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.external-binary-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-client-receive-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-client-send-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-server-receive-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.foreign-xdqp-server-send-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.journal-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.large-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.large-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-process-swap-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-system-pagein-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-system-pageout-rate', 16.639799118042, ['foo:bar']),
        ('gauge', 'hosts.memory-system-swapin-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.memory-system-swapout-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.merge-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.merge-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.query-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.read-lock-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.restore-read-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.restore-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.save-write-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.write-lock-rate', 0.0250579994171858, ['foo:bar']),
        ('gauge', 'hosts.xdqp-client-receive-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-client-send-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-server-receive-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.xdqp-server-send-rate', 0, ['foo:bar']),
        ('gauge', 'hosts.total-cpu-stat-system', 0.737475991249085, ['foo:bar']),
        ('gauge', 'hosts.total-cpu-stat-user', 1.00873005390167, ['foo:bar']),
        ('gauge', 'hosts.total-hosts', 1, ['foo:bar']),
        ('gauge', 'hosts.total-hosts-offline', 0, ['foo:bar']),
        # reauests summary
        ('gauge', 'requests.max-seconds', 0.041299, ['foo:bar']),
        ('gauge', 'requests.mean-seconds', 0.0308595, ['foo:bar']),
        ('gauge', 'requests.median-seconds', 0.0308595, ['foo:bar']),
        ('gauge', 'requests.min-seconds', 0.02042, ['foo:bar']),
        ('gauge', 'requests.ninetieth-percentile-seconds', 0.041299, ['foo:bar']),
        ('gauge', 'requests.query-count', 0, ['foo:bar']),
        ('gauge', 'requests.standard-dev-seconds', 0.0148, ['foo:bar']),
        ('gauge', 'requests.total-requests', 2, ['foo:bar']),
        ('gauge', 'requests.update-count', 2, ['foo:bar']),
        # # TODO: ignore servers-status-summary (duplicated)
        ('gauge', 'servers.expanded-tree-cache-hit-rate', 0, ['foo:bar']),
        ('gauge', 'servers.expanded-tree-cache-miss-rate', 0, ['foo:bar']),
        ('gauge', 'servers.request-count', 2, ['foo:bar']),
        ('gauge', 'servers.request-rate', 0.959999978542328, ['foo:bar']),
        # transactions summary
        ('gauge', 'transactions.max-seconds', 0.38038, ['foo:bar']),
        ('gauge', 'transactions.mean-seconds', 0.38038, ['foo:bar']),
        ('gauge', 'transactions.median-seconds', 0.38038, ['foo:bar']),
        ('gauge', 'transactions.min-seconds', 0.38038, ['foo:bar']),
        ('gauge', 'transactions.ninetieth-percentile-seconds', 0.38038, ['foo:bar']),
        ('gauge', 'transactions.standard-dev-seconds', 0, ['foo:bar']),
        ('gauge', 'transactions.total-transactions', 2, ['foo:bar']),
    ]

    result = list(parse_summary_status_base_metrics(status_base_data, ['foo:bar']))

    assert sorted(result) == sorted(EXPECTED_RESULT)


def test_parse_summary_status_resource_metrics():
    # type: () -> None
    status_resource_data = read_fixture_file('status/forests_status.yaml')

    EXPECTED_RESULT = [
        ('gauge', 'forests.backup-count', 0, ['foo:bar']),
        ('gauge', 'forests.total-load', 0, ['foo:bar']),
        ('gauge', 'forests.backup-read-load', 0, ['foo:bar']),
        ('gauge', 'forests.backup-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.database-replication-receive-load', 0, ['foo:bar']),
        ('gauge', 'forests.database-replication-send-load', 0, ['foo:bar']),
        ('gauge', 'forests.deadlock-wait-load', 0, ['foo:bar']),
        ('gauge', 'forests.journal-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.large-read-load', 0, ['foo:bar']),
        ('gauge', 'forests.large-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.merge-read-load', 0, ['foo:bar']),
        ('gauge', 'forests.merge-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.query-read-load', 0, ['foo:bar']),
        ('gauge', 'forests.read-lock-hold-load', 0, ['foo:bar']),
        ('gauge', 'forests.read-lock-wait-load', 0, ['foo:bar']),
        ('gauge', 'forests.restore-read-load', 0, ['foo:bar']),
        ('gauge', 'forests.restore-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.save-write-load', 0, ['foo:bar']),
        ('gauge', 'forests.write-lock-hold-load', 0, ['foo:bar']),
        ('gauge', 'forests.write-lock-wait-load', 0, ['foo:bar']),
        ('gauge', 'forests.max-stands-per-forest', 1, ['foo:bar']),
        ('gauge', 'forests.merge-count', 0, ['foo:bar']),
        ('gauge', 'forests.min-capacity', 98.25632, ['foo:bar']),
        ('gauge', 'forests.total-rate', 0.013826260343194, ['foo:bar']),
        ('gauge', 'forests.backup-read-rate', 0, ['foo:bar']),
        ('gauge', 'forests.backup-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.database-replication-receive-rate', 0, ['foo:bar']),
        ('gauge', 'forests.database-replication-send-rate', 0, ['foo:bar']),
        ('gauge', 'forests.deadlock-rate', 0, ['foo:bar']),
        ('gauge', 'forests.journal-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.large-read-rate', 0, ['foo:bar']),
        ('gauge', 'forests.large-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.merge-read-rate', 0, ['foo:bar']),
        ('gauge', 'forests.merge-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.query-read-rate', 0, ['foo:bar']),
        ('gauge', 'forests.read-lock-rate', 0, ['foo:bar']),
        ('gauge', 'forests.restore-read-rate', 0, ['foo:bar']),
        ('gauge', 'forests.restore-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.save-write-rate', 0, ['foo:bar']),
        ('gauge', 'forests.write-lock-rate', 0.013826260343194, ['foo:bar']),
        ('gauge', 'forests.restore-count', 0, ['foo:bar']),
        ('gauge', 'forests.state-not-open', 0, ['foo:bar']),
        ('gauge', 'forests.total-forests', 10, ['foo:bar']),
        ('gauge', 'forests.compressed-tree-cache-hit-rate', 0, ['foo:bar']),
        ('gauge', 'forests.compressed-tree-cache-miss-rate', 0, ['foo:bar']),
        ('gauge', 'forests.compressed-tree-cache-ratio', 93, ['foo:bar']),
        ('gauge', 'forests.large-binary-cache-hit-rate', 0, ['foo:bar']),
        ('gauge', 'forests.large-binary-cache-miss-rate', 0, ['foo:bar']),
        ('gauge', 'forests.list-cache-ratio', 95, ['foo:bar']),
        ('gauge', 'forests.list-cache-hit-rate', 0.0399999991059303, ['foo:bar']),
        ('gauge', 'forests.list-cache-miss-rate', 0, ['foo:bar']),
        ('gauge', 'forests.triple-cache-hit-rate', 0, ['foo:bar']),
        ('gauge', 'forests.triple-cache-miss-rate', 0, ['foo:bar']),
        ('gauge', 'forests.triple-value-cache-hit-rate', 0, ['foo:bar']),
        ('gauge', 'forests.triple-value-cache-miss-rate', 0, ['foo:bar']),
    ]

    result = list(parse_summary_status_resource_metrics('forest', status_resource_data, ['foo:bar']))

    assert sorted(result) == sorted(EXPECTED_RESULT)


def test_parse_summary_request_resource_metrics():
    summary_request_data = read_fixture_file('requests/server_Admin_requests.yaml')

    EXPECTED_RESULT = [
        ('gauge', 'request.query-count', 0, ['foo:bar']),
        ('gauge', 'request.total-requests', 0, ['foo:bar']),
        ('gauge', 'request.update-count', 0, ['foo:bar']),
    ]

    result = list(parse_summary_request_resource_metrics(summary_request_data, ['foo:bar']))

    assert sorted(result) == sorted(EXPECTED_RESULT)


def test_parse_summary_health():
    # type: () -> None
    summary_health = {
        'cluster-health-report': [
            {
                'resource-type': 'database',
                'resource-name': 'Last-Login',
                'code': 'HEALTH-DATABASE-NO-BACKUP',
                'message': 'Database has never been backed up.',
            },
            {
                'resource-type': 'database',
                'resource-name': 'Modules',
                'code': 'HEALTH-DATABASE-DISABLED',
                'message': 'Database is intentionally disabled.',
            },
            {
                'resource-type': 'database',
                'resource-name': 'Security',
                'code': 'HEALTH-DATABASE-ERROR',
                'message': 'Database error.',
            },
            {'resource-type': 'database', 'resource-name': 'Fab', 'code': 'UNKNOWN'},
        ]
    }

    EXPECTED_RESULT = [
        (
            'resource.health',
            AgentCheck.OK,
            'HEALTH-DATABASE-NO-BACKUP: Database has never been backed up.',
            ['foo:bar', 'resource:Last-Login'],
        ),
        (
            'resource.health',
            AgentCheck.WARNING,
            'HEALTH-DATABASE-DISABLED: Database is intentionally disabled.',
            ['foo:bar', 'resource:Modules'],
        ),
        (
            'resource.health',
            AgentCheck.CRITICAL,
            'HEALTH-DATABASE-ERROR: Database error.',
            ['foo:bar', 'resource:Security'],
        ),
        ('resource.health', AgentCheck.UNKNOWN, 'UNKNOWN: No message.', ['foo:bar', 'resource:Fab']),
    ]

    result = list(parse_summary_health(summary_health, ['foo:bar']))

    assert sorted(result) == sorted(EXPECTED_RESULT)
