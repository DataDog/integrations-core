# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.vault import Vault

from .common import auth_required, noauth_required
from .metrics import KNOWN_COUNTERS, METRICS, METRICS_OPTIONAL


@auth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_integration(aggregator, dd_run_check, check, instance, global_tags, use_openmetrics):
    instance = dict(instance())
    instance['use_openmetrics'] = use_openmetrics
    check = check(instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags, use_openmetrics)


@noauth_required
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_integration_noauth(aggregator, dd_run_check, check, no_token_instance, global_tags, use_openmetrics):
    instance = dict(no_token_instance)
    instance['use_openmetrics'] = use_openmetrics
    check = check(instance)
    dd_run_check(check)

    assert_collection(aggregator, global_tags, use_openmetrics)


@auth_required
@pytest.mark.e2e
@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_e2e(dd_agent_check, e2e_instance, global_tags, use_openmetrics):
    instance = dict(e2e_instance)
    instance['use_openmetrics'] = use_openmetrics
    aggregator = dd_agent_check(instance, rate=True)

    assert_collection(aggregator, global_tags, use_openmetrics, runs=2)


def assert_collection(aggregator, tags, use_openmetrics, runs=1):
    metrics = set(METRICS)
    metrics.update(METRICS_OPTIONAL)
    metrics.add('is_leader')

    # Summaries
    summaries = {'go.gc.duration.seconds'}
    summaries.update(metric for metric in metrics if metric.startswith(('vault.', 'route.')))

    # Remove everything that either is not a summary or summaries for which we're getting all 3 as NaN
    for metric in (
        'vault.audit.log.request.failure',
        'vault.audit.log.response.failure',
        'vault.expire.num_leases',
        'vault.identity.entity.creation',
        'vault.runtime.alloc.bytes',
        'vault.runtime.free.count',
        'vault.runtime.heap.objects',
        'vault.runtime.malloc.count',
        'vault.runtime.num_goroutines',
        'vault.runtime.sys.bytes',
        'vault.runtime.total.gc.runs',
        'vault.runtime.total.gc.pause_ns',
        'vault.token.count.by_policy',
        'vault.token.creation',
    ):
        summaries.remove(metric)

    summaries = {metric for metric in summaries if not metric.startswith('vault.cache.')}

    for metric in summaries:
        metrics.remove(metric)
        metrics.update({'{}.count'.format(metric), '{}.quantile'.format(metric), '{}.sum'.format(metric)})

    if use_openmetrics:
        for metric in list(metrics):
            if metric.endswith('.total'):
                metrics.discard(metric)
                metrics.add('{}.count'.format(metric[:-6]))
            elif metric in KNOWN_COUNTERS:
                metrics.discard(metric)
                metrics.add('{}.count'.format(metric))
            elif metric.startswith('vault.route.rollback.') and not metric.endswith(('.count', '.quantile', '.sum')):
                metrics.discard(metric)

    missing_summaries = defaultdict(set)
    for metric in sorted(metrics):
        at_least = 1
        if metric.startswith(tuple(METRICS_OPTIONAL)):
            at_least = 0
        metric = 'vault.{}'.format(metric)

        for tag in tags:
            try:
                aggregator.assert_metric_has_tag(metric, tag, at_least=at_least)
            # For some reason explicitly handling AssertionError does not catch AssertionError
            except Exception:
                possible_summary = re.sub(r'^vault\.|(\.count|\.quantile|\.sum)$', '', metric)
                if possible_summary in summaries:
                    missing_summaries[possible_summary].add(metric)
                else:
                    raise
            else:
                aggregator.assert_metric_has_tag_prefix(metric, 'is_leader:', at_least=at_least)
                aggregator.assert_metric_has_tag_prefix(metric, 'vault_cluster:', at_least=at_least)
                aggregator.assert_metric_has_tag_prefix(metric, 'vault_version:', at_least=at_least)
                if not use_openmetrics:
                    aggregator.assert_metric_has_tag_prefix(metric, 'cluster_name:', at_least=at_least)

    for _, summaries in sorted(missing_summaries.items()):
        if len(summaries) > 2:
            raise AssertionError('Missing: {}'.format(' | '.join(sorted(summaries))))

    aggregator.assert_all_metrics_covered()

    if use_openmetrics:
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(Vault.SERVICE_CHECK_CONNECT, Vault.OK, count=runs)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_UNSEALED, Vault.OK, count=runs)
    aggregator.assert_service_check(Vault.SERVICE_CHECK_INITIALIZED, Vault.OK, count=runs)
