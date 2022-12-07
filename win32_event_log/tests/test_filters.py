# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.win32_event_log.filters import construct_xpath_query

pytestmark = [pytest.mark.unit]


def test_no_values():
    with pytest.raises(Exception, match='No values set for property filter: source'):
        construct_xpath_query({'source': []})


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
        pytest.param(
            {'type': ['Information', 'Error', 'Warning', 'Success Audit', 'Failure audit']},
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
def test_query_construction(new_check, instance, filters, query):
    instance['filters'] = filters
    check = new_check(instance)
    check.load_configuration_models()

    assert construct_xpath_query(exclude_undefined_keys(check.config.filters.dict())) == query
