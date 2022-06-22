# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import get_check

pytestmark = [requires_py3, requires_windows]


@pytest.fixture(autouse=True)
def mock_performance_object_enumeration(mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [0]})})


class TestServer:
    def test_not_string(self, dd_run_check):
        check = get_check({'server': 9000})

        with pytest.raises(Exception, match='^Setting `server` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestUsername:
    def test_not_string(self, dd_run_check):
        check = get_check({'username': 9000})

        with pytest.raises(Exception, match='^Setting `username` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestPassword:
    def test_not_string(self, dd_run_check):
        check = get_check({'password': 9000})

        with pytest.raises(Exception, match='^Setting `password` must be a string$'):
            dd_run_check(check, extract_message=True)


class TestMetrics:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'metrics': 9000})

        with pytest.raises(Exception, match='^Setting `metrics` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_object_not_mapping(self, dd_run_check):
        check = get_check({'metrics': {'Foo': 9000}})

        with pytest.raises(Exception, match='^Performance object `Foo` in setting `metrics` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_object_name_missing(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {}}})

        with pytest.raises(Exception, match='^Option `name` for performance object `Foo` is required$'):
            dd_run_check(check, extract_message=True)

    def test_object_name_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 9000}}})

        with pytest.raises(Exception, match='^Option `name` for performance object `Foo` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_object_tag_name_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'tag_name': 9000}}})

        with pytest.raises(Exception, match='^Option `tag_name` for performance object `Foo` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_object_counters_missing(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo'}}})

        with pytest.raises(Exception, match='^Option `counters` for performance object `Foo` is required$'):
            dd_run_check(check, extract_message=True)

    def test_object_counters_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': 9000}}})

        with pytest.raises(Exception, match='^Option `counters` for performance object `Foo` must be an array$'):
            dd_run_check(check, extract_message=True)


class TestExtraMetrics:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'extra_metrics': 9000})

        with pytest.raises(Exception, match='^Setting `extra_metrics` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_object_not_mapping(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': 9000}})

        with pytest.raises(Exception, match='^Performance object `Foo` in setting `extra_metrics` must be a mapping$'):
            dd_run_check(check, extract_message=True)

    def test_object_name_missing(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': {}}})

        with pytest.raises(Exception, match='^Option `name` for performance object `Foo` is required$'):
            dd_run_check(check, extract_message=True)

    def test_object_name_not_string(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': {'name': 9000}}})

        with pytest.raises(Exception, match='^Option `name` for performance object `Foo` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_object_tag_name_not_string(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': {'name': 'foo', 'tag_name': 9000}}})

        with pytest.raises(Exception, match='^Option `tag_name` for performance object `Foo` must be a string$'):
            dd_run_check(check, extract_message=True)

    def test_object_counters_missing(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': {'name': 'foo'}}})

        with pytest.raises(Exception, match='^Option `counters` for performance object `Foo` is required$'):
            dd_run_check(check, extract_message=True)

    def test_object_counters_not_string(self, dd_run_check):
        check = get_check({'extra_metrics': {'Foo': {'name': 'foo', 'counters': 9000}}})

        with pytest.raises(Exception, match='^Option `counters` for performance object `Foo` must be an array$'):
            dd_run_check(check, extract_message=True)


class TestInclude:
    def test_not_array(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'include': 9000}}})

        with pytest.raises(Exception, match='^Option `include` for performance object `Foo` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_pattern_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'include': [9000]}}})

        with pytest.raises(
            Exception, match='^Pattern #1 of option `include` for performance object `Foo` must be a string$'
        ):
            dd_run_check(check, extract_message=True)


class TestExclude:
    def test_not_array(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'exclude': 9000}}})

        with pytest.raises(Exception, match='^Option `exclude` for performance object `Foo` must be an array$'):
            dd_run_check(check, extract_message=True)

    def test_pattern_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'exclude': [9000]}}})

        with pytest.raises(
            Exception, match='^Pattern #1 of option `exclude` for performance object `Foo` must be a string$'
        ):
            dd_run_check(check, extract_message=True)


class TestInstanceCounts:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'instance_counts': 9000}}})

        with pytest.raises(
            Exception, match='^Option `instance_counts` for performance object `Foo` must be a mapping$'
        ):
            dd_run_check(check, extract_message=True)

    def test_count_type_unknown(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'instance_counts': {'baz': '', 'bar': ''}}}})

        with pytest.raises(
            Exception, match='^Option `instance_counts` for performance object `Foo` has unknown types: bar, baz$'
        ):
            dd_run_check(check, extract_message=True)

    def test_metric_name_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'instance_counts': {'total': 9000}}}})

        with pytest.raises(
            Exception,
            match=(
                '^Metric name for count type `total` of option `instance_counts` for performance '
                'object `Foo` must be a string$'
            ),
        ):
            dd_run_check(check, extract_message=True)


class TestCounters:
    def test_not_mapping(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [9000]}}})

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Entry #1 of option `counters` for performance object `Foo` must be a mapping$'
        ):
            dd_run_check(check, extract_message=True)

    def test_invalid_type(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 9000}]}}})

        dd_run_check(check)
        with pytest.raises(Exception, match='^Counter `Bar` for performance object `Foo` must be a string or mapping$'):
            dd_run_check(check, extract_message=True)

    def test_duplicate(self, dd_run_check):
        check = get_check(
            {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar'}}, {'Bar': {'name': 'baz'}}]}}}
        )

        dd_run_check(check)
        with pytest.raises(Exception, match='^Counter `Bar` for performance object `Foo` is already defined$'):
            dd_run_check(check, extract_message=True)

    def test_metric_name_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'metric_name': 9000}}]}}})

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Option `metric_name` for counter `Bar` of performance object `Foo` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_name_missing(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {}}]}}})

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Option `name` for counter `Bar` of performance object `Foo` is required$'
        ):
            dd_run_check(check, extract_message=True)

    def test_name_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 9000}}]}}})

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Option `name` for counter `Bar` of performance object `Foo` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_type_not_string(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'type': 9000}}]}}})

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Option `type` for counter `Bar` of performance object `Foo` must be a string$'
        ):
            dd_run_check(check, extract_message=True)

    def test_type_unknown(self, dd_run_check):
        check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'type': 'baz'}}]}}})

        dd_run_check(check)
        with pytest.raises(Exception, match='^Unknown `type` for counter `Bar` of performance object `Foo`$'):
            dd_run_check(check, extract_message=True)

    def test_total_not_boolean(self, dd_run_check):
        check = get_check(
            {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'average': 9000}}]}}}
        )

        dd_run_check(check)
        with pytest.raises(
            Exception, match='^Option `average` for counter `Bar` of performance object `Foo` must be a boolean$'
        ):
            dd_run_check(check, extract_message=True)

    def test_aggregate_invalid_type(self, dd_run_check):
        check = get_check(
            {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'aggregate': 9000}}]}}}
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Option `aggregate` for counter `Bar` of performance object `Foo` must be a boolean or set to `only`$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_aggregate_not_native_metric_type(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'aggregate': True, 'type': 'time_elapsed'}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Option `aggregate` for counter `Bar` of performance object `Foo` is enabled so `type` must be set to '
                'one of the following: count, gauge, monotonic_count, rate$'
            ),
        ):
            dd_run_check(check, extract_message=True)


class TestTransformerCompilation:
    def test_temporal_percent_no_scale(self, dd_run_check):
        check = get_check(
            {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'type': 'temporal_percent'}}]}}}
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `scale` parameter is required$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_temporal_percent_unknown_scale(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'temporal_percent', 'scale': 'bar'}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `scale` parameter must be one of: '
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_temporal_percent_scale_not_int(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'temporal_percent', 'scale': 1.23}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `scale` parameter must be an integer representing parts of a second e.g. 1000 for millisecond$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_no_status_map(self, dd_run_check):
        check = get_check(
            {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'type': 'service_check'}}]}}}
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `status_map` parameter is required$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_not_dict(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': 5}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `status_map` parameter must be a mapping$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_empty(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {}}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'the `status_map` parameter must not be empty$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_value_not_number(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {True: 'OK'}}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'value `True` of parameter `status_map` does not represent an integer$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_status_not_string(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {'9000': 0}}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'status `0` for value `9000` of parameter `status_map` is not a string$'
            ),
        ):
            dd_run_check(check, extract_message=True)

    def test_service_check_status_map_status_invalid(self, dd_run_check):
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {'9000': '0k'}}}],
                    }
                }
            }
        )

        dd_run_check(check)
        with pytest.raises(
            Exception,
            match=(
                '^Error compiling transformer for counter `Bar` of performance object `Foo`: '
                'invalid status `0k` for value `9000` of parameter `status_map`$'
            ),
        ):
            dd_run_check(check, extract_message=True)


class TestSingleInstanceLogUnusedOptions:
    def test_tag_name(self, dd_run_check, mock_performance_objects, caplog):
        mock_performance_objects({'Foo': ([None], {'Bar': [9000]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'tag_name': 'baz',
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        expected_message = (
            'Ignoring option `tag_name` for performance object `Foo` since it contains single instance counters'
        )
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    def test_instance_counts(self, dd_run_check, mock_performance_objects, caplog):
        mock_performance_objects({'Foo': ([None], {'Bar': [9000]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        'instance_counts': {'total': 'baz'},
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        expected_message = (
            'Ignoring option `instance_counts` for performance object `Foo` since it contains single instance counters'
        )
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))

    @pytest.mark.parametrize('option', ['include', 'exclude'])
    def test_filters(self, dd_run_check, mock_performance_objects, caplog, option):
        mock_performance_objects({'Foo': ([None], {'Bar': [9000]})})
        check = get_check(
            {
                'metrics': {
                    'Foo': {
                        'name': 'foo',
                        option: ['baz'],
                        'counters': [{'Bar': {'name': 'bar'}}],
                    }
                }
            }
        )
        dd_run_check(check)

        expected_message = (
            'Ignoring option `{}` for performance object `Foo` since it contains single instance counters'.format(
                option
            )
        )
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))
