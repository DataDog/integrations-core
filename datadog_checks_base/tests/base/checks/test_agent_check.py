# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
from typing import Any  # noqa: F401

import mock
import pytest
from six import PY3

from datadog_checks.base import AgentCheck, to_native_string
from datadog_checks.base import __version__ as base_package_version
from datadog_checks.dev.testing import requires_py3


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


def test_persistent_cache(datadog_agent):
    check = AgentCheck()
    check.check_id = 'test'

    check.write_persistent_cache('foo', 'bar')

    assert datadog_agent.read_persistent_cache('test_foo') == 'bar'
    assert check.read_persistent_cache('foo') == 'bar'


@pytest.mark.parametrize(
    'enable_metadata_collection, expected_is_metadata_collection_enabled',
    [(None, False), ('true', True), ('false', False)],
)
def test_is_metadata_collection_enabled(enable_metadata_collection, expected_is_metadata_collection_enabled):
    check = AgentCheck()
    with mock.patch('datadog_checks.base.checks.base.datadog_agent.get_config') as get_config:
        get_config.return_value = enable_metadata_collection

        assert check.is_metadata_collection_enabled() is expected_is_metadata_collection_enabled
        assert AgentCheck.is_metadata_collection_enabled() is expected_is_metadata_collection_enabled

        get_config.assert_called_with('enable_metadata_collection')


def test_log_critical_error():
    check = AgentCheck()

    with pytest.raises(NotImplementedError):
        check.log.critical('test')


class TestSecretsSanitization:
    def test_default(self, caplog):
        # type: (Any) -> None
        secret = 's3kr3t'
        check = AgentCheck()

        message = 'hello, {}'.format(secret)
        assert check.sanitize(message) == message

        check.log.error(message)
        assert secret in caplog.text

    def test_sanitize_text(self):
        # type: () -> None
        secret = 'p@$$w0rd'
        check = AgentCheck()
        check.register_secret(secret)

        sanitized = check.sanitize('hello, {}'.format(secret))
        assert secret not in sanitized

    def text_sanitize_logs(self, caplog):
        # type: (Any) -> None
        secret = 'p@$$w0rd'
        check = AgentCheck()
        check.register_secret(secret)

        check.log.error('hello, %s', secret)
        assert secret not in caplog.text

    def test_sanitize_service_check_message(self, aggregator, caplog):
        # type: (Any, Any) -> None
        secret = 'p@$$w0rd'
        check = AgentCheck()
        check.register_secret(secret)
        sanitized = check.sanitize(secret)

        check.service_check('test.can_check', status=AgentCheck.CRITICAL, message=secret)

        aggregator.assert_service_check('test.can_check', status=AgentCheck.CRITICAL, message=sanitized)

    def test_sanitize_exception_tracebacks(self):
        # type: () -> None
        class MyCheck(AgentCheck):
            def __init__(self, *args, **kwargs):
                # type: (*Any, **Any) -> None
                super(MyCheck, self).__init__(*args, **kwargs)
                self.password = 'p@$$w0rd'
                self.register_secret(self.password)

            def check(self, instance):
                # type: (Any) -> None
                try:
                    # Simulate a failing call in a dependency.
                    raise Exception('Could not establish connection with Password={}'.format(self.password))
                except Exception as exc:
                    raise RuntimeError('Unexpected error while executing check: {}'.format(exc))

        check = MyCheck('my_check', {}, [{}])
        result = json.loads(check.run())[0]

        assert check.password not in result['message']
        assert check.password not in result['traceback']


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
        ('invalid chars', 'foo,+*-/()[]{}-  \t\nbar:123', 'foo_bar:123'),
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
        aggregator.assert_event(to_native_string(msg_text), tags=['∆', 'Ω-bar'])

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
        )
        aggregator.assert_service_check(
            "testservicecheckwithhostname",
            status=AgentCheck.OK,
            tags=["foo", "bar"],
            hostname="testhostname",
        )

        check.service_check("testservicecheckwithnonemessage", AgentCheck.OK, message=None)
        aggregator.assert_service_check("testservicecheckwithnonemessage", status=AgentCheck.OK)

    def test_sc_no_ok_message(self, aggregator):
        check = AgentCheck()
        with pytest.raises(Exception):
            check.service_check("testservicecheck", AgentCheck.OK, tags=None, message="No message allowed")

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

    def test_external_hostname(self, datadog_agent):
        check = AgentCheck()
        external_host_tags = [(u'hostnam\xe9', {'src_name': ['key1:val1']})]
        check.set_external_tags(external_host_tags)

        if PY3:
            datadog_agent.assert_external_tags(u'hostnam\xe9', {'src_name': ['key1:val1']})
        else:
            datadog_agent.assert_external_tags('hostnam\xc3\xa9', {'src_name': ['key1:val1']})

        datadog_agent.assert_external_tags_count(1)

    @pytest.mark.parametrize(
        "disable_generic_tags, expected_tags",
        [
            pytest.param(False, {"foo:bar", "cluster:my_cluster", "version", "bar"}),
            pytest.param(True, {"foo:bar", "myintegration_cluster:my_cluster", "myintegration_version", "bar"}),
        ],
    )
    def test_generic_tags(self, disable_generic_tags, expected_tags):
        instance = {'disable_generic_tags': disable_generic_tags}
        check = AgentCheck('myintegration', {}, [instance])
        tags = check._normalize_tags_type(tags=["foo:bar", "cluster:my_cluster", "version", "bar"])
        assert set(tags) == expected_tags

    @pytest.mark.parametrize(
        "exclude_metrics_filters, include_metrics_filters, expected_metrics",
        [
            pytest.param(['hello'], [], ['my_metric', 'my_metric_count', 'test.my_metric1'], id='exclude string'),
            pytest.param([r'my_metric_*'], [], ['hello'], id='exclude multiple matches glob'),
            pytest.param(
                [],
                [r'my_metricw*'],
                ['my_metric', 'my_metric_count', 'test.my_metric1'],
                id='include multiple matches glob',
            ),
            pytest.param(
                [r'my_metrics'],
                [],
                ['my_metric', 'my_metric_count', 'hello', 'test.my_metric1'],
                id='exclude no matches',
            ),
            pytest.param([r'.*'], [], [], id='exclude everything'),
            pytest.param([r'.*'], ['hello'], [], id='exclude everything one include'),
            pytest.param([], ['hello'], ['hello'], id='include string'),
            pytest.param(
                [], [r'^ns\.my_(me|test)tric*'], ['my_metric', 'my_metric_count'], id='include multiple matches'
            ),
            pytest.param([r'my_metric_count'], [r'my_metric*'], ['my_metric', 'test.my_metric1'], id='match both'),
            pytest.param([r'my_metric_count'], [r'my_metric_count'], [], id='duplicate'),
            pytest.param(
                [],
                ['metric'],
                ['my_metric', 'my_metric_count', 'test.my_metric1'],
                id='include multiple matches inside',
            ),
            pytest.param(['my_metric_count'], ['hello'], ['hello'], id='include exclude'),
            pytest.param(
                [r'testing'], [r'.*'], ['my_metric', 'my_metric_count', 'hello', 'test.my_metric1'], id='include all'
            ),
            pytest.param(
                [r'test\.my_metric([0-9]{1})'],
                [],
                [r'my_metric', r'my_metric_count', 'hello'],
                id='include all but regex',
            ),
        ],
    )
    def test_metrics_filters(self, exclude_metrics_filters, include_metrics_filters, expected_metrics, aggregator):
        instance = {
            'metric_patterns': {
                'exclude': exclude_metrics_filters,
                'include': include_metrics_filters,
            }
        }
        check = AgentCheck('myintegration', {}, [instance])
        check.__NAMESPACE__ = 'ns'
        check.gauge('my_metric', 0)
        check.count('my_metric_count', 0)
        check.count('test.my_metric1', 1)
        check.monotonic_count('hello', 0)
        check.service_check('test.can_check', status=AgentCheck.OK)

        for metric_name in expected_metrics:
            aggregator.assert_metric('ns.{}'.format(metric_name), count=1)

        aggregator.assert_service_check('ns.test.can_check', status=AgentCheck.OK)
        aggregator.assert_all_metrics_covered()

    @pytest.mark.parametrize(
        "exclude_metrics_filters, include_metrics_filters, expected_error",
        [
            pytest.param(
                'metric', [], r'^Setting `exclude` of `metric_patterns` must be an array', id='exclude not list'
            ),
            pytest.param(
                [], 'metric', r'^Setting `include` of `metric_patterns` must be an array', id='include not list'
            ),
            pytest.param(
                ['metric_one', 1000],
                [],
                r'^Entry #2 of setting `exclude` of `metric_patterns` must be a string',
                id='exclude bad element',
            ),
            pytest.param(
                [],
                [10, 'metric_one'],
                r'^Entry #1 of setting `include` of `metric_patterns` must be a string',
                id='include bad element',
            ),
        ],
    )
    def test_metrics_filter_invalid(self, aggregator, exclude_metrics_filters, include_metrics_filters, expected_error):
        instance = {
            'metric_patterns': {
                'exclude': exclude_metrics_filters,
                'include': include_metrics_filters,
            }
        }
        with pytest.raises(Exception, match=expected_error):
            AgentCheck('myintegration', {}, [instance])

    @pytest.mark.parametrize(
        "exclude_metrics_filters, include_metrics_filters, expected_log",
        [
            pytest.param(
                [''],
                [],
                'Entry #1 of setting `exclude` of `metric_patterns` must not be empty, ignoring',
                id='empty exclude',
            ),
            pytest.param(
                [],
                [''],
                'Entry #1 of setting `include` of `metric_patterns` must not be empty, ignoring',
                id='empty include',
            ),
        ],
    )
    def test_metrics_filter_warnings(self, caplog, exclude_metrics_filters, include_metrics_filters, expected_log):
        instance = {
            'metric_patterns': {
                'exclude': exclude_metrics_filters,
                'include': include_metrics_filters,
            }
        }
        caplog.clear()
        caplog.set_level(logging.DEBUG)
        AgentCheck('myintegration', {}, [instance])
        assert expected_log in caplog.text


class LimitedCheck(AgentCheck):
    DEFAULT_METRIC_LIMIT = 10

    def check(self, _):
        for i in range(5):
            self.gauge('foo', i)


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

    def test_debug_metrics_under_limit(self, aggregator, dd_run_check):
        instance = {'debug_metrics': {'metric_contexts': True}}
        check = LimitedCheck('test', {}, [instance])
        dd_run_check(check)

        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics('foo')) == 5
        aggregator.assert_metric('datadog.agent.metrics.contexts.limit', 10)
        aggregator.assert_metric('datadog.agent.metrics.contexts.total', 5)

    def test_debug_metrics_over_limit(self, aggregator, dd_run_check):
        instance = {'debug_metrics': {'metric_contexts': True}, 'max_returned_metrics': 3}
        check = LimitedCheck('test', {}, [instance])
        dd_run_check(check)

        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics('foo')) == 3
        aggregator.assert_metric('datadog.agent.metrics.contexts.limit', 3)
        aggregator.assert_metric('datadog.agent.metrics.contexts.total', 5)


class TestCheckInitializations:
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


@requires_py3
def test_load_configuration_models(dd_run_check, mocker):
    instance = {'endpoint': 'url', 'tags': ['foo:bar'], 'proxy': {'http': 'http://1.2.3.4:9000'}}
    init_config = {'proxy': {'https': 'https://1.2.3.4:4242'}}
    check = AgentCheck('test', init_config, [instance])
    check.check_id = 'test:123'
    check.check = lambda _: None

    assert check._config_model_instance is None
    assert check._config_model_shared is None

    instance_config = {}
    shared_config = {}
    package = mocker.MagicMock()
    package.InstanceConfig.model_validate = mocker.MagicMock(return_value=instance_config)
    package.SharedConfig.model_validate = mocker.MagicMock(return_value=shared_config)
    import_module = mocker.patch('importlib.import_module', return_value=package)

    dd_run_check(check)

    import_module.assert_called_with('datadog_checks.base.config_models')
    package.InstanceConfig.model_validate.assert_called_once_with(
        instance, context=check._get_config_model_context(instance)
    )
    package.SharedConfig.model_validate.assert_called_once_with(
        init_config, context=check._get_config_model_context(init_config)
    )

    assert check._config_model_instance is instance_config
    assert check._config_model_shared is shared_config


if PY3:

    from .utils import BaseModelTest

else:

    class BaseModelTest:
        def __init__(self, **kwargs):
            pass


@requires_py3
@pytest.mark.parametrize(
    "check_instance_config, default_instance_config, log_lines, unknown_options",
    [
        pytest.param(
            {
                "endpoint": "url",
                "tags": ["foo:bar"],
                "proxy": {"http": "http://1.2.3.4:9000"},
            },
            [],
            None,
            [],
            id="empty default",
        ),
        pytest.param(
            {
                "endpoint": "url",
                "tags": ["foo:bar"],
                "proxy": {"http": "http://1.2.3.4:9000"},
            },
            [
                ("endpoint", "url"),
            ],
            None,
            [],
            id="no typo",
        ),
        pytest.param(
            {
                "endpoints": "url",
                "tags": ["foo:bar"],
                "proxy": {"http": "http://1.2.3.4:9000"},
            },
            [
                ("endpoint", "url"),
            ],
            [
                (
                    "Detected potential typo in configuration option in test/instance section: `endpoints`. "
                    "Did you mean endpoint?"
                )
            ],
            ["endpoints"],
            id="typo",
        ),
        pytest.param(
            {
                "endpoints": "url",
                "tags": ["foo:bar"],
                "proxy": {"http": "http://1.2.3.4:9000"},
            },
            [
                ("endpoint", "url"),
                ("endpoints", "url"),
            ],
            None,
            [],
            id="no typo similar option",
        ),
        pytest.param(
            {
                "endpont": "url",
                "tags": ["foo:bar"],
                "proxy": {"http": "http://1.2.3.4:9000"},
            },
            [
                ("endpoint", "url"),
                ("endpoints", "url"),
            ],
            [
                (
                    "Detected potential typo in configuration option in test/instance section: `endpont`. "
                    "Did you mean endpoint, or endpoints?"
                )
            ],
            ["endpont"],
            id="typo two candidates",
        ),
        pytest.param(
            {
                "tag": "test",
            },
            [
                ("tags", "test"),
            ],
            None,
            [],
            id="short option cant catch",
        ),
        pytest.param(
            {
                "testing_long_para": "test",
            },
            [
                ("testing_long_param", "test"),
                ("test_short_param", "test"),
            ],
            [
                (
                    "Detected potential typo in configuration option in test/instance section: `testing_long_para`. "
                    "Did you mean testing_long_param?"
                )
            ],
            ["testing_long_para"],
            id="somewhat similar option",
        ),
        pytest.param(
            {
                "send_distribution_sums_as_monotonic": False,
                "exclude_labels": True,
            },
            [
                ("send_distribution_counts_as_monotonic", True),
                ("include_labels", True),
            ],
            None,
            [],
            id="different options no typos",
        ),
        pytest.param(
            {
                "send_distribution_count_as_monotonic": True,
                "exclude_label": True,
            },
            [
                ("send_distribution_sums_as_monotonic", False),
                ("send_distribution_counts_as_monotonic", True),
                ("exclude_labels", False),
                ("include_labels", True),
            ],
            [
                (
                    "Detected potential typo in configuration option in test/instance section: "
                    "`send_distribution_count_as_monotonic`. Did you mean send_distribution_counts_as_monotonic?"
                ),
                (
                    "Detected potential typo in configuration option in test/instance section: `exclude_label`. "
                    "Did you mean exclude_labels?"
                ),
            ],
            [
                "send_distribution_count_as_monotonic",
                "exclude_label",
            ],
            id="different options typo",
        ),
        pytest.param(
            {
                "field": "value",
                "schema": "my_schema",
            },
            BaseModelTest(field="my_field", schema_="the_schema"),
            None,
            [],
            id="using an alias",
        ),
        pytest.param(
            {
                "field": "value",
                "schem": "my_schema",
            },
            BaseModelTest(field="my_field", schema_="the_schema"),
            [
                (
                    "Detected potential typo in configuration option in test/instance section: "
                    "`schem`. Did you mean schema?"
                ),
            ],
            ["schem"],
            id="typo in an alias",
        ),
        pytest.param(
            {
                "field": "value",
                "schema_": "my_schema",
            },
            BaseModelTest(field="my_field", schema_="the_schema"),
            None,
            [],
            id="not using an alias",
        ),
    ],
)
def test_detect_typos_configuration_models(
    dd_run_check,
    caplog,
    check_instance_config,
    default_instance_config,
    log_lines,
    unknown_options,
):
    caplog.clear()
    caplog.set_level(logging.WARNING)
    empty_config = {}

    check = AgentCheck("test", empty_config, [check_instance_config])
    check.check_id = "test:123"

    typos = check.log_typos_in_options(check_instance_config, default_instance_config, "instance")

    if log_lines is not None:
        for log_line in log_lines:
            assert log_line in caplog.text
    else:
        assert "Detected potential typo in configuration option" not in caplog.text

    assert typos == set(unknown_options)
