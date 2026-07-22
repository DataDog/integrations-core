# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Service
from datadog_checks.base.utils.discovery.probe import (
    _discovery_noop,
    _DiscoveryAggregatorProxy,
    _DiscoveryErrorDowngrade,
    _suppress_discovery_side_effects,
    generated_discovery_candidates,
)


def test_generated_discovery_candidates_swallows_missing_discovery_module():
    class FakeCheck(AgentCheck):
        pass

    FakeCheck.__module__ = 'datadog_checks.fake_integration.checks.check'
    service = Service(id='svc', host='10.0.0.1')
    module_name = 'datadog_checks.fake_integration.config_models.discovery'

    err = ImportError('No module named ...')
    err.name = module_name

    with patch('datadog_checks.base.utils.discovery.probe.importlib.import_module', side_effect=err):
        assert list(generated_discovery_candidates(FakeCheck, service)) == []


def test_generated_discovery_candidates_swallows_missing_config_models_package():
    class FakeCheck(AgentCheck):
        pass

    FakeCheck.__module__ = 'datadog_checks.fake_integration.checks.check'
    service = Service(id='svc', host='10.0.0.1')

    err = ImportError('No module named ...')
    err.name = 'datadog_checks.fake_integration.config_models'

    with patch('datadog_checks.base.utils.discovery.probe.importlib.import_module', side_effect=err):
        assert list(generated_discovery_candidates(FakeCheck, service)) == []


def test_generated_discovery_candidates_reraises_unrelated_import_error():
    class FakeCheck(AgentCheck):
        pass

    FakeCheck.__module__ = 'datadog_checks.fake_integration.checks.check'
    service = Service(id='svc', host='10.0.0.1')

    err = ImportError('No module named ...')
    err.name = 'some_external_dependency'

    with patch('datadog_checks.base.utils.discovery.probe.importlib.import_module', side_effect=err):
        with pytest.raises(ImportError):
            generated_discovery_candidates(FakeCheck, service)


def test_suppress_discovery_side_effects_counts_metrics():
    check = AgentCheck()

    with patch('datadog_checks.base.checks.base.aggregator.submit_histogram_bucket') as submit_histogram_bucket:
        with _suppress_discovery_side_effects(check) as stats:
            assert stats.metric_count == 0
            check.gauge('my.metric', 1.0)
            check.count('my.metric', 2.0)
            check.submit_histogram_bucket('my.histogram', 3, 0, 1, True, '', [])
            assert stats.metric_count == 3

        submit_histogram_bucket.assert_not_called()

    assert stats.metric_count == 3


def test_suppress_discovery_side_effects_restores_metric_methods_after_exit():
    from datadog_checks.base.checks import base as base_module

    check = AgentCheck()

    with _suppress_discovery_side_effects(check) as stats:
        assert stats.metric_count == 0
        # proxy is set as a transient attribute; module-level aggregator is untouched
        assert isinstance(check._discovery_aggregator, _DiscoveryAggregatorProxy)
        assert 'submit_metric' not in vars(base_module.aggregator)
        assert 'submit_histogram_bucket' not in vars(base_module.aggregator)
        check.gauge('my.metric', 1.0)
        check.submit_histogram_bucket('my.histogram', 3, 0, 1, True, '', [])
        assert stats.metric_count == 2

    assert not hasattr(check, '_discovery_aggregator')
    assert 'submit_metric' not in vars(base_module.aggregator)
    assert 'submit_histogram_bucket' not in vars(base_module.aggregator)


def test_suppress_discovery_side_effects_restores_methods_after_exit():
    check = AgentCheck()

    with _suppress_discovery_side_effects(check):
        assert check.send_log is _discovery_noop

    assert check.send_log is not _discovery_noop


def test_suppress_discovery_side_effects_downgrades_error_logs():
    check = AgentCheck()

    with _suppress_discovery_side_effects(check):
        filters = check.log.logger.filters
        assert any(isinstance(f, _DiscoveryErrorDowngrade) for f in filters)

        record = logging.LogRecord(
            name='test', level=logging.ERROR, pathname='', lineno=0, msg='boom', args=(), exc_info=None
        )
        for f in filters:
            f.filter(record)

        assert record.levelno == logging.DEBUG
        assert record.levelname == 'DEBUG'

    assert not any(isinstance(f, _DiscoveryErrorDowngrade) for f in check.log.logger.filters)


def test_suppress_discovery_side_effects_does_not_touch_shared_logger():
    check = AgentCheck()
    shared_logger = check.log.logger

    with _suppress_discovery_side_effects(check):
        # check.log now points at a child logger, not the shared one
        assert check.log.logger is not shared_logger
        assert check.log.logger.name == shared_logger.name + '._discovery'
        # the shared logger must have no downgrade filter attached
        assert not any(isinstance(f, _DiscoveryErrorDowngrade) for f in shared_logger.filters)

    assert check.log.logger is shared_logger


def test_suppress_discovery_side_effects_restores_methods_on_exception():
    check = AgentCheck()

    with pytest.raises(RuntimeError):
        with _suppress_discovery_side_effects(check):
            assert check.send_log is _discovery_noop
            raise RuntimeError('body failed')

    assert check.send_log is not _discovery_noop


def test_suppress_discovery_side_effects_suppresses_aggregator_submissions():
    check = AgentCheck()

    with _suppress_discovery_side_effects(check):
        assert isinstance(check._discovery_aggregator, _DiscoveryAggregatorProxy)
        proxy = check._discovery_aggregator
        proxy.submit_event_platform_event = MagicMock()
        proxy.submit_event = MagicMock()
        proxy.submit_service_check = MagicMock()

        check.database_monitoring_query_sample('{}')
        check.database_monitoring_query_metrics('{}')
        check.database_monitoring_query_activity('{}')
        check.database_monitoring_metadata('{}')
        check.event_platform_event('{}', 'my-track')
        check.event({'msg_title': 'test', 'msg_text': 'body', 'alert_type': 'info'})
        check.service_check('my.check', AgentCheck.OK)

        assert proxy.submit_event_platform_event.call_count == 5
        assert proxy.submit_event.call_count == 1
        assert proxy.submit_service_check.call_count == 1

    # After exit, _discovery_aggregator is removed and proxy is no longer used
    check.service_check('my.check', AgentCheck.OK)
    assert proxy.submit_service_check.call_count == 1  # still 1, not 2
