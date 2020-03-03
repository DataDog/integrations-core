# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from collections import OrderedDict

import mock
import pytest
from six import PY3

from datadog_checks.base import AgentCheck
from datadog_checks.base import __version__ as base_package_version
from datadog_checks.base import to_string
from datadog_checks.base.checks.base import datadog_agent


def test_instance():
    """
    Simply assert the class can be instantiated
    """
    # rely on default
    check = AgentCheck()
    assert check.init_config == {}
    assert check.instances == []

    # pass dict for 'init_config', a list for 'instances'
    init_config = {'foo': 'bar'}
    instances = [{'bar': 'baz'}]
    check = AgentCheck(init_config=init_config, instances=instances)
    assert check.init_config == {'foo': 'bar'}
    assert check.instances == [{'bar': 'baz'}]


def test_check_version():
    check = AgentCheck()

    assert check.check_version == base_package_version


def test_load_config():
    assert AgentCheck.load_config("raw_foo: bar") == {'raw_foo': 'bar'}


def test_log_critical_error():
    check = AgentCheck()

    with pytest.raises(NotImplementedError):
        check.log.critical('test')


def test_warning_ok():
    check = AgentCheck()

    check.warning("foo")
    check.warning("hello %s%s", "world", "!")

    assert ["foo", "hello world!"] == check.warnings


def test_warning_args_errors():
    check = AgentCheck()

    check.warning("should not raise error: %s")

    with pytest.raises(TypeError):
        check.warning("not enough arguments: %s %s", "a")

    with pytest.raises(TypeError):
        check.warning("too many arguments: %s %s", "a", "b", "c")

    assert ["should not raise error: %s"] == check.warnings


@pytest.mark.parametrize(
    'case_name, check, expected_attributes',
    [
        (
            'agent 5 signature: only args',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, {'agent_conf1': 'agent_value1'}, [{'foo': 'bar'}]),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 5 signature: instances as kwarg',
            AgentCheck(
                'check_name', {'init_conf1': 'init_value1'}, {'agent_conf1': 'agent_value1'}, instances=[{'foo': 'bar'}]
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 5 signature: agentConfig and instances as kwarg',
            AgentCheck(
                'check_name',
                {'init_conf1': 'init_value1'},
                agentConfig={'agent_conf1': 'agent_value1'},
                instances=[{'foo': 'bar'}],
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 5 signature: init_config, agentConfig and instances as kwarg',
            AgentCheck(
                'check_name',
                init_config={'init_conf1': 'init_value1'},
                agentConfig={'agent_conf1': 'agent_value1'},
                instances=[{'foo': 'bar'}],
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 5 signature: name, init_config, agentConfig and instances as kwarg',
            AgentCheck(
                name='check_name',
                init_config={'init_conf1': 'init_value1'},
                agentConfig={'agent_conf1': 'agent_value1'},
                instances=[{'foo': 'bar'}],
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 5 signature: no instances',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, {'agent_conf1': 'agent_value1'}),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': None,
            },
        ),
        (
            'agent 5 signature: no instances and agentConfig as kwarg',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, agentConfig={'agent_conf1': 'agent_value1'}),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': None,
            },
        ),
        (
            'agent 5 signature: no instances and init_config, agentConfig as kwarg',
            AgentCheck(
                'check_name', init_config={'init_conf1': 'init_value1'}, agentConfig={'agent_conf1': 'agent_value1'}
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': None,
            },
        ),
        (
            'agent 5 signature: no instances and name, init_config, agentConfig as kwarg',
            AgentCheck(
                name='check_name',
                init_config={'init_conf1': 'init_value1'},
                agentConfig={'agent_conf1': 'agent_value1'},
            ),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {'agent_conf1': 'agent_value1'},
                'instance': None,
            },
        ),
        (
            'agent 6 signature: only args (instances as list)',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, [{'foo': 'bar'}]),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 6 signature: only args (instances as tuple)',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, ({'foo': 'bar'},)),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 6 signature: instances as kwarg',
            AgentCheck('check_name', {'init_conf1': 'init_value1'}, instances=[{'foo': 'bar'}]),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 6 signature: init_config, instances as kwarg',
            AgentCheck('check_name', init_config={'init_conf1': 'init_value1'}, instances=[{'foo': 'bar'}]),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {},
                'instance': {'foo': 'bar'},
            },
        ),
        (
            'agent 6 signature: name, init_config, instances as kwarg',
            AgentCheck(name='check_name', init_config={'init_conf1': 'init_value1'}, instances=[{'foo': 'bar'}]),
            {
                'name': 'check_name',
                'init_config': {'init_conf1': 'init_value1'},
                'agentConfig': {},
                'instance': {'foo': 'bar'},
            },
        ),
    ],
)
def test_agent_signature(case_name, check, expected_attributes):
    actual_attributes = {attr: getattr(check, attr) for attr in expected_attributes}
    assert expected_attributes == actual_attributes


class TestMetricNormalization:
    def test_default(self):
        check = AgentCheck()
        metric_name = u'Klüft inför på fédéral'
        normalized_metric_name = 'Kluft_infor_pa_federal'

        assert check.normalize(metric_name) == normalized_metric_name

    def test_fix_case(self):
        check = AgentCheck()
        metric_name = u'Klüft inför på fédéral'
        normalized_metric_name = 'kluft_infor_pa_federal'

        assert check.normalize(metric_name, fix_case=True) == normalized_metric_name

    def test_prefix(self):
        check = AgentCheck()
        metric_name = u'metric'
        prefix = u'somePrefix'
        normalized_metric_name = 'somePrefix.metric'

        assert check.normalize(metric_name, prefix=prefix) == normalized_metric_name

    def test_prefix_bytes(self):
        check = AgentCheck()
        metric_name = u'metric'
        prefix = b'some'
        normalized_metric_name = 'some.metric'

        assert check.normalize(metric_name, prefix=prefix) == normalized_metric_name

    def test_prefix_unicode_metric_bytes(self):
        check = AgentCheck()
        metric_name = b'metric'
        prefix = u'some'
        normalized_metric_name = 'some.metric'

        assert check.normalize(metric_name, prefix=prefix) == normalized_metric_name

    def test_prefix_fix_case(self):
        check = AgentCheck()
        metric_name = b'metric'
        prefix = u'somePrefix'
        normalized_metric_name = 'some_prefix.metric'

        assert check.normalize(metric_name, fix_case=True, prefix=prefix) == normalized_metric_name

    def test_underscores_redundant(self):
        check = AgentCheck()
        metric_name = u'a_few__redundant___underscores'
        normalized_metric_name = 'a_few_redundant_underscores'

        assert check.normalize(metric_name) == normalized_metric_name

    def test_underscores_at_ends(self):
        check = AgentCheck()
        metric_name = u'_some_underscores_'
        normalized_metric_name = 'some_underscores'

        assert check.normalize(metric_name) == normalized_metric_name

    def test_underscores_and_dots(self):
        check = AgentCheck()
        metric_name = u'some_.dots._and_._underscores'
        normalized_metric_name = 'some.dots.and.underscores'

        assert check.normalize(metric_name) == normalized_metric_name

    def test_invalid_chars_and_underscore(self):
        check = AgentCheck()
        metric_name = u'metric.hello++aaa$$_bbb'
        normalized_metric_name = 'metric.hello_aaa_bbb'

        assert check.normalize(metric_name) == normalized_metric_name


@pytest.mark.parametrize(
    'case, tag, expected_tag',
    [
        ('nothing to normalize', 'abc:123', 'abc:123'),
        ('unicode', u'Klüft inför på fédéral', 'Klüft_inför_på_fédéral'),
        ('invalid chars', 'foo,+*-/()[]{}  \t\nbar:123', 'foo_bar:123'),
        ('leading and trailing underscores', '__abc:123__', 'abc:123'),
        ('redundant underscore', 'foo_____bar', 'foo_bar'),
        ('invalid chars and underscore', 'foo++__bar', 'foo_bar'),
    ],
)
def test_normalize_tag(case, tag, expected_tag):
    check = AgentCheck()
    assert check.normalize_tag(tag) == expected_tag, 'Failed case: {}'.format(case)


class TestMetrics:
    def test_namespace(self, aggregator):
        check = AgentCheck()
        check.__NAMESPACE__ = 'test'

        check.gauge('metric', 0)

        aggregator.assert_metric('test.metric')

    def test_namespace_override(self, aggregator):
        check = AgentCheck()
        check.__NAMESPACE__ = 'test'

        methods = ('gauge', 'count', 'monotonic_count', 'rate', 'histogram', 'historate', 'increment', 'decrement')
        for method in methods:
            getattr(check, method)('metric', 0, raw=True)

        aggregator.assert_metric('metric', count=len(methods))

    def test_non_float_metric(self, aggregator):
        check = AgentCheck()
        metric_name = 'test_metric'
        with pytest.raises(ValueError):
            check.gauge(metric_name, '85k')
        aggregator.assert_metric(metric_name, count=0)


class TestEvents:
    def test_valid_event(self, aggregator):
        check = AgentCheck()
        event = {
            "event_type": "new.event",
            "msg_title": "new test event",
            "aggregation_key": "test.event",
            "msg_text": "test event test event",
            "tags": ["foo", "bar"],
            "timestamp": 1,
        }
        check.event(event)
        aggregator.assert_event('test event test event', tags=["foo", "bar"])

    @pytest.mark.parametrize('msg_text', [u'test-π', 'test-π', b'test-\xcf\x80'])
    def test_encoding(self, aggregator, msg_text):
        check = AgentCheck()
        event = {
            'event_type': 'new.event',
            'msg_title': 'new test event',
            'aggregation_key': 'test.event',
            'msg_text': msg_text,
            'tags': ['∆', u'Ω-bar'],
            'timestamp': 1,
        }
        check.event(event)
        aggregator.assert_event(to_string(msg_text), tags=['∆', 'Ω-bar'])

    def test_namespace(self, aggregator):
        check = AgentCheck()
        check.__NAMESPACE__ = 'test'
        event = {
            'event_type': 'new.event',
            'msg_title': 'new test event',
            'aggregation_key': 'test.event',
            'msg_text': 'test event test event',
            'tags': ['foo', 'bar'],
            'timestamp': 1,
        }
        check.event(event)
        aggregator.assert_event('test event test event', source_type_name='test', tags=['foo', 'bar'])


class TestServiceChecks:
    def test_valid_sc(self, aggregator):
        check = AgentCheck()

        check.service_check("testservicecheck", AgentCheck.OK, tags=None, message="")
        aggregator.assert_service_check("testservicecheck", status=AgentCheck.OK)

        check.service_check(
            "testservicecheckwithhostname",
            AgentCheck.OK,
            tags=["foo", "bar"],
            hostname="testhostname",
            message="a message",
        )
        aggregator.assert_service_check(
            "testservicecheckwithhostname",
            status=AgentCheck.OK,
            tags=["foo", "bar"],
            hostname="testhostname",
            message="a message",
        )

        check.service_check("testservicecheckwithnonemessage", AgentCheck.OK, message=None)
        aggregator.assert_service_check("testservicecheckwithnonemessage", status=AgentCheck.OK)

    def test_namespace(self, aggregator):
        check = AgentCheck()
        check.__NAMESPACE__ = 'test'

        check.service_check('service_check', AgentCheck.OK)
        aggregator.assert_service_check('test.service_check', status=AgentCheck.OK)

    def test_namespace_override(self, aggregator):
        check = AgentCheck()
        check.__NAMESPACE__ = 'test'

        check.service_check('service_check', AgentCheck.OK, raw=True)
        aggregator.assert_service_check('service_check', status=AgentCheck.OK)


class TestTags:
    def test_default_string(self):
        check = AgentCheck()
        tag = 'default:string'
        tags = [tag]

        normalized_tags = check._normalize_tags_type(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        # Ensure no new allocation occurs
        assert normalized_tag is tag

    def test_bytes_string(self):
        check = AgentCheck()
        tag = b'bytes:string'
        tags = [tag]

        normalized_tags = check._normalize_tags_type(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags

        if PY3:
            assert normalized_tag == tag.decode('utf-8')
        else:
            # Ensure no new allocation occurs
            assert normalized_tag is tag

    def test_unicode_string(self):
        check = AgentCheck()
        tag = u'unicode:string'
        tags = [tag]

        normalized_tags = check._normalize_tags_type(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags

        if PY3:
            # Ensure no new allocation occurs
            assert normalized_tag is tag
        else:
            assert normalized_tag == tag.encode('utf-8')

    def test_unicode_device_name(self):
        check = AgentCheck()
        tags = []
        device_name = u'unicode_string'

        normalized_tags = check._normalize_tags_type(tags, device_name)
        normalized_device_tag = normalized_tags[0]

        assert isinstance(normalized_device_tag, str if PY3 else bytes)

    def test_duplicated_device_name(self):
        check = AgentCheck()
        tags = []
        device_name = 'foo'
        check._normalize_tags_type(tags, device_name)
        normalized_tags = check._normalize_tags_type(tags, device_name)
        assert len(normalized_tags) == 1

    def test_none_value(self, caplog):
        check = AgentCheck()
        tags = [None, 'tag:foo']

        normalized_tags = check._normalize_tags_type(tags, None)
        assert normalized_tags == ['tag:foo']
        assert 'Error encoding tag' not in caplog.text

    def test_external_host_tag_normalization(self):
        """
        Tests that the external_host_tag modifies in place the list of tags in the provided object
        """
        check = AgentCheck()
        external_host_tags = [('hostname', {'src_name': ['key1:val1']})]
        with mock.patch.object(check, '_normalize_tags_type', return_value=['normalize:tag']):
            check.set_external_tags(external_host_tags)
            assert external_host_tags == [('hostname', {'src_name': ['normalize:tag']})]

    def test_external_hostname(self):
        check = AgentCheck()
        external_host_tags = [(u'hostnam\xe9', {'src_name': ['key1:val1']})]
        with mock.patch.object(datadog_agent, 'set_external_tags') as set_external_tags:
            check.set_external_tags(external_host_tags)
            if PY3:
                set_external_tags.assert_called_with([(u'hostnam\xe9', {'src_name': ['key1:val1']})])
            else:
                set_external_tags.assert_called_with([('hostnam\xc3\xa9', {'src_name': ['key1:val1']})])


class LimitedCheck(AgentCheck):
    DEFAULT_METRIC_LIMIT = 10


class TestLimits:
    def test_context_uid(self, aggregator):
        check = LimitedCheck()

        # Test stability of the hash against tag ordering
        uid = check._context_uid(aggregator.GAUGE, "test.metric", ["one", "two"], None)
        assert uid == check._context_uid(aggregator.GAUGE, "test.metric", ["one", "two"], None)
        assert uid == check._context_uid(aggregator.GAUGE, "test.metric", ["two", "one"], None)

        # Test all fields impact the hash
        assert uid != check._context_uid(aggregator.RATE, "test.metric", ["one", "two"], None)
        assert uid != check._context_uid(aggregator.GAUGE, "test.metric2", ["one", "two"], None)
        assert uid != check._context_uid(aggregator.GAUGE, "test.metric", ["two"], None)
        assert uid != check._context_uid(aggregator.GAUGE, "test.metric", ["one", "two"], "host")

    def test_metric_limit_gauges(self, aggregator):
        check = LimitedCheck()
        assert check.get_warnings() == []

        for _ in range(0, 10):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 10

        for _ in range(0, 10):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 10

    def test_metric_limit_count(self, aggregator):
        check = LimitedCheck()
        assert check.get_warnings() == []

        # Multiple calls for a single set of (metric_name, tags) should not trigger
        for _ in range(0, 20):
            check.count("metric", 0, hostname="host-single")
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 20

        # Multiple sets of tags should trigger
        # Only 9 new sets of tags should pass through
        for i in range(0, 20):
            check.count("metric", 0, hostname="host-{}".format(i))
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 29

    def test_metric_limit_instance_config(self, aggregator):
        instances = [{"max_returned_metrics": 42}]
        check = AgentCheck("test", {}, instances)
        assert check.get_warnings() == []

        for _ in range(0, 42):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 42

        check.gauge("metric", 0)
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 42

    def test_metric_limit_instance_config_zero_limited(self, aggregator):
        instances = [{"max_returned_metrics": 0}]
        check = LimitedCheck("test", {}, instances)
        assert len(check.get_warnings()) == 1

        for _ in range(0, 42):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 1  # get_warnings resets the array
        assert len(aggregator.metrics("metric")) == 10

    def test_metric_limit_instance_config_zero_unlimited(self, aggregator):
        instances = [{"max_returned_metrics": 0}]
        check = AgentCheck("test", {}, instances)
        assert len(check.get_warnings()) == 0

        for _ in range(0, 42):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 0  # get_warnings resets the array
        assert len(aggregator.metrics("metric")) == 42

    def test_metric_limit_instance_config_string(self, aggregator):
        instances = [{"max_returned_metrics": "4"}]
        check = AgentCheck("test", {}, instances)
        assert check.get_warnings() == []

        for _ in range(0, 4):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 4

        check.gauge("metric", 0)
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 4

    @pytest.mark.parametrize(
        "max_returned_metrics",
        (
            pytest.param("I am not a int-convertible string", id="value-error"),
            pytest.param(None, id="type-error-1"),
            pytest.param(["A list is not an int"], id="type-error-2"),
        ),
    )
    def test_metric_limit_instance_config_invalid_int(self, aggregator, max_returned_metrics):
        instances = [{"max_returned_metrics": max_returned_metrics}]
        check = LimitedCheck("test", {}, instances)
        assert len(check.get_warnings()) == 1

        # Should have fell back to the default metric limit.
        for _ in range(12):
            check.gauge("metric", 0)
        assert len(aggregator.metrics("metric")) == 10


class TestCheckInitializations:
    def test_default(self):
        class TestCheck(AgentCheck):
            def check(self, _):
                pass

        check = TestCheck('test', {}, [{}])
        check.check_id = 'test:123'

        with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
            check.run()

            assert m.call_count == 0

    def test_default_config_sent(self):
        class TestCheck(AgentCheck):
            METADATA_DEFAULT_CONFIG_INIT_CONFIG = ['foo']
            METADATA_DEFAULT_CONFIG_INSTANCE = ['bar']

            def check(self, _):
                pass

        # Ordered by call order in `AgentCheck.send_config_metadata`
        value_map = OrderedDict((('instance', 'mock'), ('init_config', 5)))

        config = {'foo': value_map['init_config'], 'bar': value_map['instance']}
        check = TestCheck('test', config, [config])
        check.check_id = 'test:123'

        with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
            check.run()

            assert m.call_count == 2
            check.run()
            assert m.call_count == 2

            for (config_type, value), call_args in zip(value_map.items(), m.call_args_list):
                args, _ = call_args
                assert args[0] == 'test:123'
                assert args[1] == 'config.{}'.format(config_type)

                data = json.loads(args[2])[0]

                assert data.pop('is_set', None) is True
                assert data.pop('value', None) == value
                assert not data

    def test_success_only_once(self):
        class TestCheck(AgentCheck):
            def __init__(self, *args, **kwargs):
                super(TestCheck, self).__init__(*args, **kwargs)
                self.state = 1
                self.initialize = mock.MagicMock(side_effect=self._initialize)
                self.check_initializations.append(self.initialize)

            def _initialize(self):
                self.state += 1
                if self.state % 2:
                    raise Exception('is odd')

            def check(self, _):
                pass

        check = TestCheck('test', {}, [{}])
        check.run()
        check.run()
        check.run()

        assert check.initialize.call_count == 1

    def test_error_retry(self):
        class TestCheck(AgentCheck):
            def __init__(self, *args, **kwargs):
                super(TestCheck, self).__init__(*args, **kwargs)
                self.state = 0
                self.initialize = mock.MagicMock(side_effect=self._initialize)
                self.check_initializations.append(self.initialize)

            def _initialize(self):
                self.state += 1
                if self.state % 2:
                    raise Exception('is odd')

            def check(self, _):
                pass

        check = TestCheck('test', {}, [{}])
        check.run()
        check.run()
        check.run()

        assert check.initialize.call_count == 2
