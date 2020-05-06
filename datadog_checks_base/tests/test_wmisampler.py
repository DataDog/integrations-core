# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from tests.utils import requires_windows

try:
    from datadog_checks.base.checks.win.wmi import WMISampler
except ImportError:
    pass


@requires_windows
@pytest.mark.unit
def test_format_filter_value():
    filters = [{'a': 'b'}, {'c': 'd'}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( c = 'd' ) OR ( a = 'b' )"


@requires_windows
@pytest.mark.unit
def test_format_filter_like():
    filters = [{'a': '%foo'}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a LIKE '%foo' )"


@requires_windows
@pytest.mark.unit
def test_format_filter_list_expected():
    filters = [{'a': ['<', 3]}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a < '3' )"


@requires_windows
@pytest.mark.unit
def test_format_filter_tuple():
    # needed for backwards compatibility and hardcoded filters
    filters = [{'a': ('<', 3)}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a < '3' )"


@requires_windows
@pytest.mark.unit
def test_format_filter_win32_log():
    query = {
        'TimeGenerated': ('>=', '202056101355.000000+'),
        'Type': [('=', 'Warning')],
        'SourceName': [('=', 'MSSQLSERVER')],
    }

    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=[query])
    formatted_filters = sampler.formatted_filters
    assert (
        formatted_filters == " WHERE ( ( SourceName = 'MSSQLSERVER' ) "
        "AND ( Type = 'Warning' ) AND TimeGenerated >= '202056101355.000000+' )"
    )
