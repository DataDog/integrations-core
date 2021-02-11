# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.win32_event_log.filters import construct_xpath_query

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'filters, query',
    [
        pytest.param({}, '*', id='no filters'),
        pytest.param({'source': ['foo']}, "*[System[Provider[@Name='foo']]]", id='source single'),
        pytest.param(
            {'source': ['foo', 'bar']}, "*[System[Provider[(@Name='bar' or @Name='foo')]]]", id='source multiple'
        ),
        pytest.param({'type': ['Success']}, '*[System[Level=4]]', id='type Success'),
        pytest.param({'type': ['Error']}, '*[System[Level=2]]', id='type Error'),
        pytest.param({'type': ['Warning']}, '*[System[Level=3]]', id='type Warning'),
        pytest.param({'type': ['Information']}, '*[System[Level=4]]', id='type Information'),
        pytest.param({'type': ['Success Audit']}, "*[System[Keywords='0x8020000000000000']]", id='type Success Audit'),
        pytest.param({'type': ['Failure Audit']}, "*[System[Keywords='0x8010000000000000']]", id='type Failure Audit'),
        pytest.param({'type': ['Failure Audit']}, "*[System[Keywords='0x8010000000000000']]", id='type Failure Audit'),
        pytest.param(
            {'type': ['Information', 'Error', 'Warning', 'Success Audit', 'Failure Audit']},
            "*[System[(Level=2 or Level=3 or Level=4 or "
            "Keywords='0x8010000000000000' or Keywords='0x8020000000000000')]]",
            id='type multiple',
        ),
        pytest.param({'id': [5678]}, '*[System[EventID=5678]]', id='id single'),
        pytest.param({'id': [5678, 1234]}, '*[System[(EventID=1234 or EventID=5678)]]', id='id multiple'),
        pytest.param(
            {'type': ['Information', 'Error', 'Warning'], 'id': [5678, 1234], 'source': ['foo', 'bar']},
            (
                "*["
                "System[Provider[(@Name='bar' or @Name='foo')] "
                "and (EventID=1234 or EventID=5678) "
                "and (Level=2 or Level=3 or Level=4)]"
                "]"
            ),
            id='complex',
        ),
    ],
)
def test_query_construction(filters, query):
    assert construct_xpath_query(filters) == query


class TestBasicValidation:
    def test_unknown_filter(self):
        with pytest.raises(Exception, match='Unknown property filter: foo'):
            construct_xpath_query({'foo': 'bar'})

    def test_no_values(self):
        with pytest.raises(Exception, match='No values set for property filter: source'):
            construct_xpath_query({'source': []})


class TestSourceValidation:
    def test_value_not_string(self):
        with pytest.raises(Exception, match='Values for event filter `source` must be strings.'):
            construct_xpath_query({'source': [0]})


class TestTypeValidation:
    def test_value_not_string(self):
        with pytest.raises(Exception, match='Values for event filter `type` must be strings.'):
            construct_xpath_query({'type': [0]})

    def test_unknown_value(self):
        with pytest.raises(Exception, match='Unknown value for event filter `type`: foo'):
            construct_xpath_query({'type': ['foo']})


class TestIdValidation:
    def test_value_not_integer(self):
        with pytest.raises(Exception, match='Values for event filter `id` must be integers.'):
            construct_xpath_query({'id': ['foo']})
