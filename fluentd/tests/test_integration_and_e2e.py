# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.fluentd import Fluentd

from .common import CHECK_NAME, HOST, INSTANCE_WITH_PLUGIN
from .util import _get_metrics_by_version


def assert_basic_case(aggregator):
    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']

    aggregator.assert_service_check('fluentd.is_ok', status=Fluentd.OK, tags=sc_tags, count=2)

    for m in _get_metrics_by_version():
        aggregator.assert_metric('{0}.{1}'.format(CHECK_NAME, m), tags=['plugin_id:plg1'])

    aggregator.assert_all_metrics_covered()


def assert_discovery_case(aggregator):
    # Discovery doesn't know about `plugin_ids`, so the generated candidate has no filter
    # and metrics are emitted for every plugin, unlike `assert_basic_case`'s `plg1`-only instance.
    # Discovery also connects through the container's actual (dynamic) IP and the Agent enriches
    # its tags with container tags (docker_image, image_name, and so on), so exact tag equality
    # can't be asserted here: the service check is checked without tags, and metrics use
    # `assert_metric_has_tags` instead of `assert_metric`.
    aggregator.assert_service_check('fluentd.is_ok', status=Fluentd.OK, count=2)

    for m in _get_metrics_by_version():
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric_has_tags(metric_name, ['plugin_id:plg1'])
        aggregator.assert_metric_has_tags(metric_name, ['plugin_id:plg2'])

    aggregator.assert_all_metrics_covered()


def test_discovery_candidate_omits_secure_fluentd_default() -> None:
    service = Service(id='fluentd', host='10.0.0.1', ports=(Port(number=24220),))

    candidates = list(Fluentd.generate_configs(service))

    assert len(candidates) == 1
    assert 'fluentd' not in candidates[0]['init_config']
    assert 'fluentd' not in candidates[0]['instances'][0]
    assert candidates[0]['instances'][0]['monitor_agent_url'] == 'http://10.0.0.1:24220/api/plugins.json'


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_basic_case_integration(aggregator, dd_run_check):
    instance = copy.deepcopy(INSTANCE_WITH_PLUGIN)
    check = Fluentd(CHECK_NAME, {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    assert_basic_case(aggregator)


@pytest.mark.e2e
def test_basic_case_e2e(dd_agent_check):
    instance = copy.deepcopy(INSTANCE_WITH_PLUGIN)
    aggregator = dd_agent_check(instance, rate=True)

    assert_basic_case(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    assert_discovery_case(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, Fluentd)
