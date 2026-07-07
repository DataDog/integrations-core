# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import confluent_kafka as ck
import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mapr import MaprCheck
from datadog_checks.mapr import mapr as mapr_module
from datadog_checks.mapr.common import ALLOWED_METRICS, COUNT_METRICS, GAUGE_METRICS, MONOTONIC_COUNTER_METRICS
from datadog_checks.mapr.utils import get_stream_id_for_topic

from .common import DISTRIBUTION_METRIC, KAFKA_METRIC, METRICS_IN_FIXTURE, STREAM_ID_FIXTURE


@pytest.mark.unit
def test_metrics_constants():
    """Make sure those sets have a two-by-two empty intersection"""
    for m in ALLOWED_METRICS:
        total = 0
        if m in GAUGE_METRICS:
            total += 1
        elif m in COUNT_METRICS:
            total += 1
        elif m in MONOTONIC_COUNTER_METRICS:
            total += 1

        assert total == 1


@pytest.mark.unit
def test_get_stream_id():
    for (text, rng), value in STREAM_ID_FIXTURE.items():
        assert get_stream_id_for_topic(text, rng=rng) == value


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_whitelist(instance):
    instance['metric_whitelist'] = [r'mapr\.fs.*', r'mapr\.db.*']
    check = MaprCheck('mapr', {}, [instance])

    for m in ALLOWED_METRICS:
        if m.startswith('mapr.fs') or m.startswith('mapr.db'):
            assert check.should_collect_metric(m)
        else:
            assert not check.should_collect_metric(m)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_gauge(instance, aggregator):
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(KAFKA_METRIC)

    aggregator.assert_metric(
        'mapr.process.context_switch_involuntary',
        value=6308,
        tags=[
            'mapr_cluster:demo',
            'process_name:apiserver',
            'mapr_cluster_id:7616098736519857348',
            'fqdn:mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
        ],
    )


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_gauge_additional_tags(instance, aggregator):
    instance['tags'] = ["foo:bar", "baz:biz"]
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(KAFKA_METRIC)

    aggregator.assert_metric(
        'mapr.process.context_switch_involuntary',
        tags=[
            'mapr_cluster:demo',
            'process_name:apiserver',
            'mapr_cluster_id:7616098736519857348',
            'fqdn:mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
            'foo:bar',
            'baz:biz',
        ],
    )


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_bucket(instance, aggregator):
    check = MaprCheck('mapr', {}, [instance])
    check.submit_metric(DISTRIBUTION_METRIC)
    expected_tags = [
        "mapr_cluster_id:7616098736519857348",
        "mapr_cluster:demo",
        "fqdn:mapr-lab-2-dhk4.c.datadog-integrations-lab.internal",
        "noindex://primary",
        "rpc_type:put",
        "table_fid:2070.42.262546",
        "table_path:/var/mapr/mapr.monitoring/tsdb-meta",
    ]
    aggregator.assert_histogram_bucket('mapr.db.table.latency', 21, 2, 5, False, 'stubbed.hostname', expected_tags)
    aggregator.assert_histogram_bucket('mapr.db.table.latency', 11, 5, 10, False, 'stubbed.hostname', expected_tags)
    aggregator.assert_all_metrics_covered()  # No metrics submitted


@pytest.mark.usefixtures("mock_getconnection")
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check(aggregator, instance):
    check = MaprCheck('mapr', {}, [instance])
    check.check(instance)

    for m in METRICS_IN_FIXTURE:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_default_instance_attributes(instance):
    check = MaprCheck('mapr', {}, [instance])
    # Kills core/NumberReplacer at mapr.py:48 (streams_count default 1 -> 2).
    assert check.streams_count == 1
    # Kills core/ReplaceFalseWithTrue at mapr.py:56 (has_ever_submitted_metrics default False -> True).
    assert check.has_ever_submitted_metrics is False


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_disable_legacy_cluster_tag_defaults_to_false():
    # Kills core/ReplaceFalseWithTrue at mapr.py:57 (disable_legacy_cluster_tag default False -> True).
    check = MaprCheck('mapr', {}, [{'ticket_location': 'foo'}])
    assert check._disable_legacy_cluster_tag is False


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn")
def test_missing_auth_ticket_does_not_raise(monkeypatch):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot at mapr.py:60 (`if not self.auth_ticket`); flipping
    # it sends a ticket-less config into `os.access(None, ...)`, which raises instead of just warning.
    monkeypatch.delenv('MAPR_TICKETFILE_LOCATION', raising=False)
    check = MaprCheck('mapr', {}, [{}])
    assert check.auth_ticket is None


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check_raises_when_confluent_kafka_unavailable(instance, monkeypatch):
    # Kills the core/ReplaceBinaryOperator_Mod_* family at mapr.py:80 (the `%` op formatting ck_import_error); any
    # other operator raises TypeError against the exception object instead of the intended CheckException.
    monkeypatch.setattr(mapr_module, 'ck', None)
    monkeypatch.setattr(mapr_module, 'ck_import_error', ImportError('boom'))
    check = MaprCheck('mapr', {}, [instance])
    with pytest.raises(CheckException, match='boom'):
        check.check(instance)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check_reraises_and_flags_critical_on_connection_error(instance, aggregator, monkeypatch):
    # Kills core/ExceptionReplacer at mapr.py:85 and the core/ReplaceBinaryOperator_Add_* family at mapr.py:87; a
    # connection failure must be caught, flagged CRITICAL with the tag list intact, and re-raised unchanged.
    check = MaprCheck('mapr', {}, [instance])
    monkeypatch.setattr(check, 'get_connection', mock.Mock(side_effect=ValueError('boom')))
    with pytest.raises(ValueError, match='boom'):
        check.check(instance)
    aggregator.assert_service_check('mapr.can_connect', AgentCheck.CRITICAL, tags=['topic:{}'.format(check.topic_path)])


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check_no_messages_skips_submitted_metric(instance, aggregator, monkeypatch):
    check = MaprCheck('mapr', {}, [instance])
    fake_conn = mock.Mock(poll=mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'get_connection', mock.Mock(return_value=fake_conn))
    check.check(instance)
    # Kills core/NumberReplacer at mapr.py:93 (submitted_metrics_count init 0 -> 1/-1).
    aggregator.assert_metric('mapr.metrics.submitted', count=0)
    # Kills core/NumberReplacer at mapr.py:98 (poll timeout=0.5 -> 1.5/-0.5).
    fake_conn.poll.assert_called_once_with(timeout=0.5)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_check_skips_error_log_when_already_submitted_before(instance, monkeypatch):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot at mapr.py:109
    # (`if not self.has_ever_submitted_metrics`); once metrics were seen before, an empty poll must not re-log the
    # "never collected" error.
    check = MaprCheck('mapr', {}, [instance])
    check.has_ever_submitted_metrics = True
    check.log = mock.Mock()
    fake_conn = mock.Mock(poll=mock.Mock(return_value=None))
    monkeypatch.setattr(check, 'get_connection', mock.Mock(return_value=fake_conn))
    check.check(instance)
    check.log.error.assert_not_called()


@pytest.mark.unit
@pytest.mark.usefixtures("mock_getconnection", "mock_fqdn", "mock_ticket_file_readable")
def test_check_marks_has_ever_submitted_metrics_after_success(instance):
    # Kills core/AddNot at mapr.py:111 and core/ReplaceTrueWithFalse at mapr.py:112; submitting metrics must flip
    # has_ever_submitted_metrics from False to True.
    check = MaprCheck('mapr', {}, [instance])
    assert check.has_ever_submitted_metrics is False
    check.check(instance)
    assert check.has_ever_submitted_metrics is True


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_metric_uses_first_element_of_batch(instance, aggregator):
    # Kills core/NumberReplacer at mapr.py:127 ([0] -> [-1]); only the first JSON element in the batch is processed.
    check = MaprCheck('mapr', {}, [instance])
    msg = mock.Mock(
        value=mock.Mock(
            return_value=json.dumps(
                [
                    {'metric': 'mapr.process.rss', 'value': 1, 'tags': {}},
                    {'metric': 'mapr.process.vm', 'value': 2, 'tags': {}},
                ]
            )
        )
    )
    check._process_metric(msg)
    aggregator.assert_metric('mapr.process.rss', value=1)
    aggregator.assert_metric('mapr.process.vm', count=0)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_metric_returns_one_when_collected(instance):
    # Kills core/NumberReplacer at mapr.py:133 (return 1 -> 2) once a metric is accepted.
    check = MaprCheck('mapr', {}, [instance])
    msg = mock.Mock(value=mock.Mock(return_value=json.dumps([{'metric': 'mapr.process.rss', 'value': 1, 'tags': {}}])))
    assert check._process_metric(msg) == 1


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_metric_returns_zero_when_not_collected(instance):
    # Kills core/NumberReplacer at mapr.py:134 (return 0 -> 1/-1) when the metric is filtered out.
    check = MaprCheck('mapr', {}, [instance])
    msg = mock.Mock(value=mock.Mock(return_value=json.dumps([{'metric': 'totally.unknown', 'value': 1, 'tags': {}}])))
    assert check._process_metric(msg) == 0


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_metric_swallows_malformed_message(instance):
    # Kills core/ExceptionReplacer at mapr.py:135; malformed messages must be caught and logged, not propagated.
    check = MaprCheck('mapr', {}, [instance])
    msg = mock.Mock(value=mock.Mock(return_value='not valid json'))
    assert check._process_metric(msg) is None


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_error_topic_auth_with_ticket_raises_permission_message(instance):
    # Kills the core/ReplaceComparisonOperator_Eq_NotEq/_Lt/_Gt/_IsNot and core/AddNot mutants at mapr.py:140, plus
    # the `%`-on-tuple core/ReplaceBinaryOperator_Mod_* family at mapr.py:144; a ticketed
    # TOPIC_AUTHORIZATION_FAILED error must raise the ticket-specific permission message.
    check = MaprCheck('mapr', {}, [instance])
    error_msg = mock.Mock(code=mock.Mock(return_value=ck.KafkaError.TOPIC_AUTHORIZATION_FAILED))
    with pytest.raises(CheckException, match="does not have the 'consume' permission"):
        check._process_error(error_msg)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn")
def test_process_error_topic_auth_without_ticket_raises_generic_message(monkeypatch):
    # Kills core/AddNot at mapr.py:141 (`if self.auth_ticket`) and the `%`-on-tuple
    # core/ReplaceBinaryOperator_Mod_* family at mapr.py:151; a ticket-less TOPIC_AUTHORIZATION_FAILED error must
    # raise the impersonation-guidance message instead.
    monkeypatch.delenv('MAPR_TICKETFILE_LOCATION', raising=False)
    check = MaprCheck('mapr', {}, [{}])
    error_msg = mock.Mock(code=mock.Mock(return_value=ck.KafkaError.TOPIC_AUTHORIZATION_FAILED))
    with pytest.raises(CheckException, match="impersonation is correctly configured"):
        check._process_error(error_msg)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_error_code_above_partition_eof_raises_generic_error(instance):
    # Kills core/ReplaceComparisonOperator_Eq_GtE at mapr.py:140 and the
    # core/ReplaceComparisonOperator_NotEq_Eq/_Lt/_Is family at mapr.py:153; a code that's neither
    # TOPIC_AUTHORIZATION_FAILED nor _PARTITION_EOF, and sorts above both, must raise the raw error unchanged.
    check = MaprCheck('mapr', {}, [instance])
    error_msg = mock.Mock(code=mock.Mock(return_value=100))
    with pytest.raises(CheckException) as exc_info:
        check._process_error(error_msg)
    assert exc_info.value.args[0] is error_msg


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_error_code_below_partition_eof_raises_generic_error(instance):
    # Kills core/ReplaceComparisonOperator_Eq_LtE at mapr.py:140 and the
    # core/ReplaceComparisonOperator_NotEq_Gt/_GtE family at mapr.py:153; a code that sorts below both known codes
    # must still raise the raw error unchanged.
    check = MaprCheck('mapr', {}, [instance])
    error_msg = mock.Mock(code=mock.Mock(return_value=-300))
    with pytest.raises(CheckException) as exc_info:
        check._process_error(error_msg)
    assert exc_info.value.args[0] is error_msg


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_error_partition_eof_is_silently_ignored(instance):
    # Kills the core/ReplaceComparisonOperator_NotEq_Eq/_LtE/_GtE/_Is family at mapr.py:153; a genuine
    # _PARTITION_EOF error is expected at end-of-partition and must not raise.
    check = MaprCheck('mapr', {}, [instance])
    error_msg = mock.Mock(code=mock.Mock(return_value=ck.KafkaError._PARTITION_EOF))
    check._process_error(error_msg)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_process_error_partition_eof_by_value_is_silently_ignored(instance):
    # Kills core/ReplaceComparisonOperator_NotEq_IsNot at mapr.py:153; a code that equals _PARTITION_EOF by value
    # but isn't the same object must still be treated as EOF, not raise.
    check = MaprCheck('mapr', {}, [instance])
    distinct_eof_code = int(str(ck.KafkaError._PARTITION_EOF))
    error_msg = mock.Mock(code=mock.Mock(return_value=distinct_eof_code))
    check._process_error(error_msg)


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_get_connection_returns_cached_connection(instance):
    # Kills core/AddNot at mapr.py:159 (`if self._conn`); an existing connection must be reused, not recreated.
    check = MaprCheck('mapr', {}, [instance])
    sentinel = object()
    check._conn = sentinel
    assert check.get_connection() is sentinel


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_get_connection_disables_auto_commit(instance, monkeypatch):
    # Kills core/ReplaceFalseWithTrue at mapr.py:166; the consumer must disable auto-commit so offsets aren't
    # persisted between check runs.
    check = MaprCheck('mapr', {}, [instance])
    fake_ck = mock.Mock()
    monkeypatch.setattr(mapr_module, 'ck', fake_ck)
    check.get_connection()
    assert fake_ck.Consumer.call_args[0][0]['enable.auto.commit'] is False


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_should_collect_metric_rejects_unknown_metric(instance):
    # Kills core/ReplaceFalseWithTrue at mapr.py:176; metrics outside the allowed set must never be collected.
    check = MaprCheck('mapr', {}, [instance])
    assert check.should_collect_metric('totally.unknown.metric') is False


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_metric_only_special_cases_exact_clusterid_key(instance, aggregator):
    # Kills core/ReplaceComparisonOperator_Eq_LtE at mapr.py:198; a tag key that merely sorts before "clusterid"
    # must be passed through as-is, not treated as the special clusterid tag.
    check = MaprCheck('mapr', {}, [instance])
    metric = {'metric': 'mapr.process.rss', 'value': 42, 'tags': {'a': 'v'}}
    check.submit_metric(metric)
    aggregator.assert_metric('mapr.process.rss', value=42, tags=['a:v'])


@pytest.mark.unit
@pytest.mark.usefixtures("mock_fqdn", "mock_ticket_file_readable")
def test_submit_metric_requires_both_buckets_and_histogram_membership(instance, aggregator):
    # Kills core/ReplaceAndWithOr at mapr.py:206; a metric with `buckets` that isn't in HISTOGRAM_METRICS must
    # still be submitted via its own type, not treated as a histogram bucket.
    check = MaprCheck('mapr', {}, [instance])
    metric = {'metric': 'mapr.process.rss', 'value': 42, 'buckets': {'1,2': 5}, 'tags': {}}
    check.submit_metric(metric)
    aggregator.assert_metric('mapr.process.rss', value=42)


@pytest.mark.unit
def test_get_stream_id_default_rng_uses_shortcut():
    # Kills core/NumberReplacer at utils.py:7 (rng default 1 -> 2/0); with the default rng, the result must be the
    # rng==1 shortcut (0), not a hash computed with a different modulus.
    assert get_stream_id_for_topic('streamalpha') == 0


@pytest.mark.unit
def test_get_stream_id_zero_rng_falls_through_to_hash():
    # Kills core/ReplaceComparisonOperator_Eq_Lt/_LtE and core/NumberReplacer (rng==1 -> rng==0) at utils.py:12;
    # rng=0 must not hit the rng==1 shortcut and instead blow up computing `h % rng`.
    with pytest.raises(ZeroDivisionError):
        get_stream_id_for_topic('streamalpha', rng=0)


@pytest.mark.unit
def test_get_stream_id_rng_two_uses_hash_not_shortcut():
    # Kills core/NumberReplacer at utils.py:12 (rng==1 -> rng==2); rng=2 must go through the real hash computation.
    assert get_stream_id_for_topic('streamalpha', rng=2) == 1
