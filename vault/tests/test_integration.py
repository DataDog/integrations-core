# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

import pytest

from datadog_checks.vault import Vault

from .common import auth_required, noauth_required
from .metrics import METRICS


@auth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_integration(aggregator, dd_run_check, check, instance, global_tags):
    instance = instance()
    check = check(instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags)


@noauth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_integration_noauth(aggregator, dd_run_check, check, no_token_instance, global_tags):
    check = check(no_token_instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags)


@auth_required
@pytest.mark.e2e
def test_e2e(dd_agent_check, e2e_instance, global_tags):
    aggregator = dd_agent_check(e2e_instance, rate=True)

    assert_collection(aggregator, global_tags, runs=2)


def assert_collection(aggregator, tags, runs=1):
    metrics = set(METRICS)
    metrics.add('is_leader')

    # Remove metrics that only appear occasionally
    for metric in list(metrics):
        if metric.startswith(('vault.rollback.', 'vault.route.rollback.', 'vault.cache.')):
            metrics.remove(metric)

    # Summaries
    summaries = {'go.gc.duration.seconds'}
    summaries.update(metric for metric in metrics if metric.startswith('vault.'))

    # Remove everything that either is not a summary or summaries for which we're getting all 3 as NaN
    for metric in (
        'vault.audit.log.request.failure',
        'vault.expire.num_leases',
        'vault.runtime.alloc.bytes',
        'vault.runtime.free.count',
        'vault.runtime.heap.objects',
        'vault.runtime.malloc.count',
        'vault.runtime.num_goroutines',
        'vault.runtime.sys.bytes',
        'vault.runtime.total.gc.pause_ns',
        'vault.runtime.total.gc.runs',
    ):
        summaries.remove(metric)

    summaries = {metric for metric in summaries if not metric.startswith('vault.cache.')}

    for metric in summaries:
        metrics.remove(metric)
        metrics.update({'{}.count'.format(metric), '{}.quantile'.format(metric), '{}.sum'.format(metric)})

    missing_summaries = defaultdict(set)
    for metric in sorted(metrics):
        metric = 'vault.{}'.format(metric)

        for tag in tags:
            try:
                aggregator.assert_metric_has_tag(metric, tag)
            # For some reason explicitly handling AssertionError does not catch AssertionError
            except Exception:
                possible_summary = re.sub(r'^vault\.|(\.count|\.quantile|\.sum)$', '', metric)
                if possible_summary in summaries:
                    missing_summaries[possible_summary].add(metric)
                else:
                    raise
            else:
                aggregator.assert_metric_has_tag_prefix(metric, 'is_leader:')
                aggregator.assert_metric_has_tag_prefix(metric, 'vault_cluster:')
                aggregator.assert_metric_has_tag_prefix(metric, 'cluster_name:')
                aggregator.assert_metric_has_tag_prefix(metric, 'vault_version:')

    for _, summaries in sorted(missing_summaries.items()):
        if len(summaries) > 2:
            raise AssertionError('Missing: {}'.format(' | '.join(sorted(summaries))))

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, Vault.OK, count=runs)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, Vault.OK, count=runs)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, Vault.OK, count=runs)
