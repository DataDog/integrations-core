# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import mock
import pytest

from datadog_checks.base.utils.discovery import Discovery, Port, Service, candidate_ports, candidate_ports_by_name


def test_include_empty():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items)
    assert list(d.get_items()) == []
    assert mock_get_items.mock_calls == [mock.call()]


def test_include_empty_exclude_non_empty():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, exclude=['b.*'])
    assert list(d.get_items()) == []
    assert mock_get_items.mock_calls == [mock.call()]


def test_include_empty_limit():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=1)
    assert list(d.get_items()) == []
    assert mock_get_items.mock_calls == [mock.call()]


@pytest.mark.parametrize(
    'pattern',
    [
        pytest.param(
            'a.*',
            id='with string',
        ),
        pytest.param(
            re.compile('a.*'),
            id='with compiled pattern',
        ),
    ],
)
def test_include_not_empty(pattern):
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={pattern: None})
    assert list(d.get_items()) == [(pattern, 'a', 'a', None)]
    assert mock_get_items.mock_calls == [mock.call()]


def test_include_processed_in_order():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'c.*': {'value': 5}, 'a.*': {'value': 10}})
    assert list(d.get_items()) == [('c.*', 'c', 'c', {'value': 5}), ('a.*', 'a', 'a', {'value': 10})]
    assert mock_get_items.mock_calls == [mock.call()]


def test_exclude_and_include_intersection_is_empty():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'a.*': None}, exclude=['b.*'])
    assert list(d.get_items()) == [('a.*', 'a', 'a', None)]
    assert mock_get_items.mock_calls == [mock.call()]


def test_exclude_is_subset_of_include():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, include={'.*': None}, exclude=['b.*'])
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.mock_calls == [mock.call()]


def test_exclude_is_equals_to_include():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(limit=10, include={'b.*': None}, exclude=['b.*'], interval=0, get_items_func=mock_get_items)
    assert list(d.get_items()) == []
    assert mock_get_items.mock_calls == [mock.call()]


def test_limit_zero():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=0, include={'.*': None})
    assert list(d.get_items()) == []
    assert mock_get_items.mock_calls == [mock.call()]


def test_limit_none():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=None, include={'.*': None})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.mock_calls == [mock.call()]


def test_limit_greater_than_zero():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=5, include={'.*': {'value': 5}})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', {'value': 5}),
        ('.*', 'b', 'b', {'value': 5}),
        ('.*', 'c', 'c', {'value': 5}),
        ('.*', 'd', 'd', {'value': 5}),
        ('.*', 'e', 'e', {'value': 5}),
    ]
    assert mock_get_items.mock_calls == [mock.call()]


def test_limit_greater_than_items_len():
    mock_get_items = mock.Mock(return_value=['a', 'b', 'c', 'd', 'e', 'f', 'g'])
    d = Discovery(mock_get_items, limit=10, include={'.*': None})
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
        ('.*', 'e', 'e', None),
        ('.*', 'f', 'f', None),
        ('.*', 'g', 'g', None),
    ]
    assert mock_get_items.mock_calls == [mock.call()]


def test_interval_none_two_calls_to_get_items_func():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    d = Discovery(mock_get_items, include={'.*': None}, interval=None)
    assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
    ]
    assert mock_get_items.mock_calls == [mock.call(), mock.call()]


def test_interval_zero_two_calls_to_get_items_func():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    d = Discovery(mock_get_items, include={'.*': None})
    assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
    assert list(d.get_items()) == [
        ('.*', 'a', 'a', None),
        ('.*', 'b', 'b', None),
        ('.*', 'c', 'c', None),
        ('.*', 'd', 'd', None),
    ]
    assert mock_get_items.mock_calls == [mock.call(), mock.call()]


def test_interval_not_exceeded():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    with mock.patch('time.time', side_effect=[100, 120]):
        d = Discovery(mock_get_items, include={'.*': None}, interval=60)
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert mock_get_items.mock_calls == [mock.call()]


def test_interval_exceeded():
    mock_get_items = mock.Mock(side_effect=[['a', 'b'], ['a', 'b', 'c', 'd']])
    with mock.patch('time.time', side_effect=[100, 168, 168]):
        d = Discovery(mock_get_items, include={'.*': None}, interval=60)
        assert list(d.get_items()) == [('.*', 'a', 'a', None), ('.*', 'b', 'b', None)]
        assert list(d.get_items()) == [
            ('.*', 'a', 'a', None),
            ('.*', 'b', 'b', None),
            ('.*', 'c', 'c', None),
            ('.*', 'd', 'd', None),
        ]
        assert mock_get_items.mock_calls == [mock.call(), mock.call()]


def test_key_in_items():
    mock_get_items = mock.Mock(return_value=[{'key': 'a', 'value': 75}, {'key': 'b', 'value': 89}])
    d = Discovery(mock_get_items, include={'a.*': {'filter': 'xxxx'}}, key=lambda item: item['key'])
    assert list(d.get_items()) == [('a.*', 'a', {'key': 'a', 'value': 75}, {'filter': 'xxxx'})]
    assert mock_get_items.mock_calls == [mock.call()]


def test_candidate_ports_prefers_hints_and_deduplicates():
    service = Service(
        id='svc',
        host='127.0.0.1',
        ports=(
            Port(number=8080, name='http'),
            Port(number=9090, name='metrics'),
            Port(number=8081, name='admin'),
        ),
    )

    assert list(candidate_ports(service, [9090, 9090, 1234])) == [
        Port(number=9090, name='metrics'),
        Port(number=8080, name='http'),
        Port(number=8081, name='admin'),
    ]


@pytest.mark.parametrize(
    "ports, names, expected",
    [
        pytest.param(
            (
                Port(number=8080, name='http'),
                Port(number=9090, name='metrics'),
                Port(number=8081, name='admin'),
            ),
            ['metrics', 'http-prom'],
            [Port(number=9090, name='metrics')],
            id="only_yields_matching_ports",
        ),
        pytest.param(
            (
                Port(number=8080, name='bar'),
                Port(number=9090, name='foo'),
                Port(number=8081, name='bar'),
                Port(number=9091, name='foo'),
            ),
            ['foo', 'bar'],
            [
                Port(number=9090, name='foo'),
                Port(number=9091, name='foo'),
                Port(number=8080, name='bar'),
                Port(number=8081, name='bar'),
            ],
            id="respects_name_priority",
        ),
        pytest.param(
            (
                Port(number=8080, name='http'),
                Port(number=8081, name='admin'),
            ),
            ['metrics'],
            [],
            id="does_not_fallback_to_other_ports",
        ),
        pytest.param(
            (
                Port(number=8443, name='metrics'),
                Port(number=8443, name='http-metrics'),
                Port(number=9443, name='metrics'),
            ),
            ['http-metrics', 'metrics'],
            [
                Port(number=8443, name='http-metrics'),
                Port(number=9443, name='metrics'),
            ],
            id="deduplicates_matching_port_numbers",
        ),
        pytest.param(
            (Port(number=8080, name=''),),
            [''],
            [],
            id="ignores_empty_names",
        ),
    ],
)
def test_candidate_ports_by_name(ports, names, expected):
    service = Service(id='svc', host='127.0.0.1', ports=ports)
    assert list(candidate_ports_by_name(service, names)) == expected


def test_dev_placeholder_field_constants_match_models():
    """Guard the one fact datadog_checks_dev must hand-copy from base.

    The discovery tooling cannot import datadog_checks_base, so it keeps the
    Service/Port field names as constants used to validate candidate-template
    placeholders. This test fails if those constants drift from the real models.
    """
    pytest.importorskip('datadog_checks.dev.tooling.configuration.discovery.registry')
    from datadog_checks.dev.tooling.configuration.discovery.registry import PORT_FIELDS, SERVICE_FIELDS

    assert SERVICE_FIELDS == set(Service.model_fields)
    assert PORT_FIELDS == set(Port.model_fields)


def test_discovery_strategy_passes_complete_contexts():
    from datadog_checks.base.utils.discovery import discovery_strategy

    @discovery_strategy(provides=('port',))
    def my_strategy(service):
        yield {'port': 8080}

    assert list(my_strategy(None)) == [{'port': 8080}]


def test_discovery_strategy_raises_on_missing_key():
    from datadog_checks.base.utils.discovery import discovery_strategy

    @discovery_strategy(provides=('port', 'host'))
    def bad_strategy(service):
        yield {'port': 8080}

    with pytest.raises(ValueError, match="did not provide declared keys"):
        list(bad_strategy(None))
