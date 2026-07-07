# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from copy import deepcopy
from itertools import chain

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.silk import SilkCheck
from datadog_checks.silk.events import SilkEvent
from datadog_checks.silk.metrics import BLOCKSIZE_METRICS, METRICS, READ_WRITE_METRICS, Metric

from .common import HOST, mock_get_data

pytestmark = [pytest.mark.unit]


def test_submit_system_state_error(instance, caplog):
    caplog.set_level(logging.DEBUG)
    check = SilkCheck('silk', {}, [instance])

    check._get_data = mock.MagicMock(side_effect=[(None, 404)])
    check.submit_system_state()

    assert (
        "Could not access system state and version info, got response code `404` from endpoint `system/state`"
        in caplog.text
    )


@pytest.mark.parametrize(
    'get_data_url, expected_metrics, metrics_to_collect',
    [
        pytest.param(
            'system__bs_breakdown=True.json',  # `?` had to be removed to pass windows CI
            [
                'silk.system.block_size.io_ops.avg',
                'silk.system.block_size.latency.inner',
                'silk.system.block_size.latency.outer',
                'silk.system.block_size.throughput.avg',
            ],
            {
                'stats/system?__bs_breakdown=True': Metric(
                    **{
                        'prefix': 'system.block_size',
                        'metrics': {
                            'iops_avg': 'io_ops.avg',
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'resolution': 'resolution',
                            'bs': 'block_size',
                        },
                    }
                )
            },
            id="system bs metrics",
        ),
        pytest.param(
            'volumes__bs_breakdown=True.json',
            [
                'silk.volume.block_size.io_ops.avg',
                'silk.volume.block_size.latency.inner',
                'silk.volume.block_size.latency.outer',
                'silk.volume.block_size.throughput.avg',
            ],
            {
                'stats/volumes?__bs_breakdown=True': Metric(
                    **{
                        'prefix': 'volume.block_size',
                        'metrics': {
                            'iops_avg': ('io_ops.avg', 'gauge'),
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'peer_k2_name': 'peer_name',
                            'volume_name': 'volume_name',
                            'resolution': 'resolution',
                            'bs': 'block_size',
                        },
                    }
                )
            },
            id="volume bs metrics",
        ),
        pytest.param(
            'volumes__rw_breakdown=True.json',
            [
                'silk.volume.read.io_ops.avg',
                'silk.volume.read.latency.inner',
                'silk.volume.read.latency.outer',
                'silk.volume.read.throughput.avg',
                'silk.volume.write.io_ops.avg',
                'silk.volume.write.latency.inner',
                'silk.volume.write.latency.outer',
                'silk.volume.write.throughput.avg',
            ],
            {
                'stats/volumes?__rw_breakdown=True': Metric(
                    **{
                        'prefix': 'volume',
                        'metrics': {
                            'iops_avg': ('io_ops.avg', 'gauge'),
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'peer_k2_name': 'peer_name',
                            'volume_name': 'volume_name',
                            'resolution': 'resolution',
                        },
                        'field_to_name': {
                            'rw': {
                                'r': 'read',
                                'w': 'write',
                            }
                        },
                    }
                )
            },
            id="volume rw metrics",
        ),
        pytest.param(
            'system__rw_breakdown=True.json',
            [
                'silk.system.read.io_ops.avg',
                'silk.system.read.latency.inner',
                'silk.system.read.latency.outer',
                'silk.system.read.throughput.avg',
                'silk.system.write.io_ops.avg',
                'silk.system.write.latency.inner',
                'silk.system.write.latency.outer',
                'silk.system.write.throughput.avg',
            ],
            {
                'stats/system?__rw_breakdown=True': Metric(
                    **{
                        'prefix': 'system',
                        'metrics': {
                            'iops_avg': 'io_ops.avg',
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'resolution': 'resolution',
                        },
                        'field_to_name': {
                            'rw': {
                                'r': 'read',
                                'w': 'write',
                            }
                        },
                    }
                )
            },
            id="system rw metrics",
        ),
    ],
)
def test_bs_rw_metrics(aggregator, instance, get_data_url, expected_metrics, metrics_to_collect):
    check = SilkCheck('silk', {}, [instance])
    check._get_data = mock.MagicMock(side_effect=mock_get_data(get_data_url))
    check.metrics_to_collect = metrics_to_collect
    base_tags = ['silk_host:localhost:80', 'system_id:5501', 'system_name:K2-5501', 'test:silk']
    check.collect_metrics(base_tags)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)


@pytest.mark.parametrize(
    'enable_rw, enable_bs, extra_metrics_to_collect',
    [
        pytest.param(False, False, {}, id="both disabled"),
        pytest.param(True, True, dict(chain(BLOCKSIZE_METRICS.items(), READ_WRITE_METRICS.items())), id="both enabled"),
        pytest.param(False, True, deepcopy(BLOCKSIZE_METRICS), id="bs enabled"),
        pytest.param(True, False, deepcopy(READ_WRITE_METRICS), id="rw enabled"),
    ],
)
def test_metrics_to_collect(instance, enable_rw, enable_bs, extra_metrics_to_collect):
    inst = deepcopy(instance)
    inst['enable_read_write_statistics'] = enable_rw
    inst['enable_blocksize_statistics'] = enable_bs

    check = SilkCheck('silk', {}, [inst])

    expected_metrics_to_collect = deepcopy(METRICS)
    expected_metrics_to_collect.update(extra_metrics_to_collect)
    assert sorted(check.metrics_to_collect.keys()) == sorted(expected_metrics_to_collect.keys())


def test_unreachable_endpoint(dd_run_check, aggregator):
    invalid_instance = {'host_address': 'http://{}:81'.format(HOST)}
    check = SilkCheck('silk', {}, [invalid_instance])

    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_service_check('silk.can_connect', SilkCheck.CRITICAL)


def test_incorrect_config(dd_run_check):
    invalid_instance = {'host_addres': 'localhost'}  # misspelled required parameter
    with pytest.raises(ConfigurationError):
        SilkCheck('silk', {}, [invalid_instance])


def test_optional_metric_groups_disabled_by_default(instance):
    # Kills the core/ReplaceFalseWithTrue mutants at check.py:37 and check.py:40
    # (the `enable_read_write_statistics`/`enable_blocksize_statistics` .get() defaults flip to True).
    inst = deepcopy(instance)
    inst.pop('enable_read_write_statistics', None)
    inst.pop('enable_blocksize_statistics', None)

    check = SilkCheck('silk', {}, [inst])

    assert sorted(check.metrics_to_collect.keys()) == sorted(METRICS.keys())


def test_collect_metrics_swallows_generic_exception(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:71 (except Exception -> except CosmicRayTestingException).
    caplog.set_level(logging.DEBUG)
    check = SilkCheck('silk', {}, [instance])
    check.metrics_to_collect = {'some/path': Metric(prefix='p', metrics={'m': 'm'})}
    check._get_data = mock.MagicMock(side_effect=RuntimeError('boom'))

    check.collect_metrics([])

    assert "Encountered error getting Silk metrics for path some/path: boom" in caplog.text


def test_submit_system_state_uses_first_hit_and_concatenates_tags(instance, aggregator):
    # Kills the core/NumberReplacer mutants at check.py:85 (response_hits[0] -> [1] / [-1]) and the
    # core/ReplaceBinaryOperator_Add_* mutants at check.py:95 (system_tags + self._tags).
    check = SilkCheck('silk', {}, [instance])
    hits = [
        {'state': 'online', 'system_name': 'FIRST', 'system_id': '1'},
        {'state': 'degraded', 'system_name': 'SECOND', 'system_id': '2'},
    ]
    check._get_data = mock.MagicMock(return_value=(hits, 200))

    system_tags = check.submit_system_state()

    assert system_tags == ['system_name:FIRST', 'system_id:1']
    aggregator.assert_service_check('silk.system.state', SilkCheck.OK, tags=system_tags + check._tags, count=1)


def test_submit_version_metadata_present(instance, datadog_agent):
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:1'

    check._submit_version_metadata('6.0.102.25')

    datadog_agent.assert_metadata(
        'test:1',
        {
            'version.scheme': 'silk',
            'version.major': '6',
            'version.minor': '0',
            'version.patch': '102',
            'version.release': '25',
            'version.raw': '6.0.102.25',
        },
    )


def test_submit_version_metadata_missing_version_skips_parsing(instance, caplog):
    # Kills the core/AddNot mutant at check.py:134 (`if version:` -> `if not version:`).
    caplog.set_level(logging.DEBUG)
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:1'

    check._submit_version_metadata(None)

    assert "Could not submit version metadata, got: None" in caplog.text


def test_submit_version_metadata_malformed_version_logged(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:146 (except Exception -> except CosmicRayTestingException).
    caplog.set_level(logging.DEBUG)
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:1'

    check._submit_version_metadata('6.0.102')  # missing the 4th `.`-separated segment, unpacking raises ValueError

    assert "Could not parse version" in caplog.text


def test_submit_version_metadata_skipped_when_metadata_collection_disabled(instance, datadog_agent):
    # Kills the core/RemoveDecorator mutant at check.py:132 (@AgentCheck.metadata_entrypoint removed).
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:1'
    datadog_agent._config['enable_metadata_collection'] = False

    check._submit_version_metadata('6.0.102.25')

    datadog_agent.assert_metadata_count(0)


def test_submit_server_state_reraises_and_logs_generic_exception(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:109 (except Exception -> except CosmicRayTestingException).
    caplog.set_level(logging.WARNING)
    check = SilkCheck('silk', {}, [instance])
    check._get_data = mock.MagicMock(side_effect=RuntimeError('boom'))

    with pytest.raises(RuntimeError):
        check.submit_server_state()

    assert "Encountered error getting Silk server state: boom" in caplog.text


def test_submit_server_state_reports_per_server_status_and_tags(instance, aggregator):
    # Kills the core/AddNot mutant at check.py:114, the core/ZeroIterationForLoop mutant at check.py:115,
    # the core/ReplaceBinaryOperator_Add_* mutants at check.py:117, and the core/ReplaceComparisonOperator_Eq_*
    # and core/AddNot mutants at check.py:122 (state == OK_STATE).
    check = SilkCheck('silk', {}, [instance])
    servers = [
        {'name': 'server-a', 'status': 'OK'},
        {'name': 'server-b', 'status': 'Degraded'},
        {'name': 'server-c', 'status': 'Warning'},
    ]
    check._get_data = mock.MagicMock(return_value=(servers, 200))

    check.submit_server_state()

    aggregator.assert_service_check(
        'silk.server.state', SilkCheck.OK, tags=check._tags + ['server_name:server-a'], count=1
    )
    aggregator.assert_service_check(
        'silk.server.state', SilkCheck.UNKNOWN, tags=check._tags + ['server_name:server-b'], count=1
    )
    aggregator.assert_service_check(
        'silk.server.state', SilkCheck.UNKNOWN, tags=check._tags + ['server_name:server-c'], count=1
    )
    aggregator.assert_service_check('silk.server.state', count=3)


def test_parse_metrics_applies_item_tags(aggregator, instance):
    # Kills the core/ZeroIterationForLoop mutant at check.py:165 and the core/AddNot mutant at check.py:166
    # (`for key, tag_name in metrics_mapping.tags.items()` / `if key in item`).
    check = SilkCheck('silk', {}, [instance])
    metric_obj = Metric(
        prefix='volume',
        metrics={'iops_avg': ('io_ops.avg', 'gauge')},
        tags={'volume_name': 'volume_name'},
    )
    output = [{'iops_avg': 42, 'volume_name': 'vol-1'}]

    check.parse_metrics(output, 'stats/volumes', tags=['base:tag'], metrics_mapping=metric_obj, get_method=getattr)

    aggregator.assert_metric('silk.volume.io_ops.avg', value=42, tags=['base:tag', 'volume_name:vol-1'])


def test_get_data_reports_error_message_from_response(instance, aggregator):
    # Kills the core/AddNot mutant at check.py:193 and the core/ReplaceBinaryOperator_Add_* mutants at check.py:194
    # (`"Received error message: " + response_json.get('error_msg')`).
    check = SilkCheck('silk', {}, [instance])
    fake_response = mock.MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.status_code = 200
    fake_response.json.return_value = {'error_msg': 'boom'}
    check._http = mock.MagicMock(get=mock.MagicMock(return_value=fake_response))

    hits, code = check._get_data('some/path')

    assert hits is None
    assert code == 200
    aggregator.assert_service_check(
        'silk.can_connect', SilkCheck.WARNING, message='Received error message: boom', count=1
    )


def test_get_data_returns_hits_when_no_error_message(instance, aggregator):
    # Kills the core/ReplaceAndWithOr mutant at check.py:193
    # (`response_json and 'error_msg' in response_json` -> `response_json or ...`).
    check = SilkCheck('silk', {}, [instance])
    fake_response = mock.MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.status_code = 200
    fake_response.json.return_value = {'hits': ['a', 'b']}
    check._http = mock.MagicMock(get=mock.MagicMock(return_value=fake_response))

    hits, code = check._get_data('some/path')

    assert hits == ['a', 'b']
    assert code == 200
    aggregator.assert_service_check('silk.can_connect', count=0)


def test_get_data_reraises_and_logs_generic_exception(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:199 (except Exception -> except CosmicRayTestingException).
    caplog.set_level(logging.WARNING)
    check = SilkCheck('silk', {}, [instance])
    check._http = mock.MagicMock(get=mock.MagicMock(side_effect=RuntimeError('boom')))

    with pytest.raises(RuntimeError):
        check._get_data('some/path')

    assert "Encountered error while getting data from some/path: boom" in caplog.text


def test_collect_events_combines_tags_for_every_event(instance, aggregator):
    # Kills the core/ReplaceBinaryOperator_Add_* mutants at check.py:213 (self._tags + system_tags) and the
    # core/ZeroIterationForLoop mutant at check.py:214 (`for event in raw_events`).
    check = SilkCheck('silk', {}, [instance])
    raw_events = [
        {'timestamp': 1, 'name': 'n1', 'message': 'test_event1', 'user': 'alice'},
        {'timestamp': 2, 'name': 'n2', 'message': 'test_event2', 'user': 'bob'},
    ]
    check._get_data = mock.MagicMock(return_value=(raw_events, 200))

    check.collect_events(['system_id:5501'])

    aggregator.assert_event('test_event1', count=1, tags=check._tags + ['system_id:5501', 'user:alice'])
    aggregator.assert_event('test_event2', count=1, tags=check._tags + ['system_id:5501', 'user:bob'])
    aggregator.assert_event('test_event', count=2, exact_match=False)


def test_collect_events_logs_malformed_event_without_generic_wrapper(instance):
    # Kills the core/ExceptionReplacer mutant at check.py:219
    # (except ValueError -> except CosmicRayTestingException), which would let the malformed-event error escape
    # the inner handler and get logged by the outer, differently-formatted handler instead.
    check = SilkCheck('silk', {}, [instance])
    raw_events = [{'name': 'n1', 'message': 'test_event1', 'user': 'alice'}]  # no timestamp
    check._get_data = mock.MagicMock(return_value=(raw_events, 200))
    check.log = mock.MagicMock()

    check.collect_events([])

    check.log.error.assert_called_once_with("Event has no timestamp, will not submit event")


def test_collect_events_logs_and_continues_after_get_data_error(instance, caplog):
    # Kills the core/ExceptionReplacer mutant at check.py:222 (except Exception -> except CosmicRayTestingException).
    caplog.set_level(logging.ERROR)
    check = SilkCheck('silk', {}, [instance])
    check._get_data = mock.MagicMock(side_effect=RuntimeError('boom'))

    check.collect_events([])  # must not raise

    assert "Unable to fetch events: boom" in caplog.text


def test_silk_event_missing_timestamp_raises():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at events.py:8.
    with pytest.raises(ValueError, match="Event has no timestamp, will not submit event"):
        SilkEvent({"name": "n", "message": "m"}, ["t"])


def test_silk_event_missing_name_raises():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at events.py:10.
    with pytest.raises(ValueError, match="Event has no name, will not submit event"):
        SilkEvent({"timestamp": 1, "message": "m"}, ["t"])


def test_silk_event_missing_message_raises():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at events.py:12.
    with pytest.raises(ValueError, match="Event has no message, will not submit event"):
        SilkEvent({"timestamp": 1, "name": "n"}, ["t"])


def test_silk_event_defaults_raw_event_to_empty_dict():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at events.py:18
    # (`raw_event is None` -> `raw_event = {}`); without the default, validating `None` raises AttributeError
    # instead of the expected ValueError.
    with pytest.raises(ValueError, match="Event has no timestamp, will not submit event"):
        SilkEvent(None, ["t"])


def test_silk_event_defaults_tags_to_empty_list():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at events.py:20
    # (`tags is None` -> `tags = []`); without the default, appending to `tags[:]` raises TypeError on None.
    raw_event = {"timestamp": 1, "name": "n", "message": "m", "user": "alice"}

    event = SilkEvent(raw_event, tags=None)

    assert event.get_datadog_payload()["tags"] == ["user:alice"]


def test_silk_event_appends_user_tag_via_string_formatting():
    # Kills the core/ReplaceBinaryOperator_Mod_* mutants at events.py:33 (`'user:%s' % raw_event.get("user")`).
    raw_event = {"timestamp": 1, "name": "n", "message": "m", "user": "alice"}

    event = SilkEvent(raw_event, ["base:tag"])

    assert event.get_datadog_payload()["tags"] == ["base:tag", "user:alice"]


def test_metric_keeps_provided_tags_when_truthy():
    # Kills the core/AddNot mutant at metrics.py:24 (`tags if tags else {}` -> `tags if not tags else {}`).
    m = Metric(prefix='p', metrics={}, tags={'a': 'b'})

    assert m.tags == {'a': 'b'}
