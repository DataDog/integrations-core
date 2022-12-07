# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections

from datadog_checks.dev.testing import requires_windows

try:
    from datadog_checks.base.checks.win.wmi import WMISampler
except ImportError:
    pass


try:
    from datadog_checks.base.checks.win.wmi.sampler import CaseInsensitiveDict
except ImportError:
    pass


@requires_windows
def test_format_filter_value():
    filters = [{'a': 'b'}, {'c': 'd'}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( c = 'd' ) OR ( a = 'b' )"


@requires_windows
def test_format_filter_like():
    filters = [{'a': '%foo'}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a LIKE '%foo' )"


@requires_windows
def test_format_filter_list_expected():
    filters = [{'a': ['<', 3]}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a < '3' )"

    filters = [{'a': ['three', 3]}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( ( a = 'three' OR a = '3' ) )"


@requires_windows
def test_format_filter_tuple():
    # needed for backwards compatibility and hardcoded filters
    filters = [{'a': ('<', 3)}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a < '3' )"


@requires_windows
def test_format_filter_bool_op_alt():
    filters = [{'a': {'OR': [['>=', 10], ['<', 0]]}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( ( a >= '10' OR a < '0' ) )"

    filters = [{'a': {'AND': [['<>', 'c'], ['<>', 'd']]}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( ( a <> 'c' AND a <> 'd' ) )"

    filters = [{'a': {'NOR': ['c', 'd']}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( NOT ( a = 'c' OR a = 'd' ) )"

    filters = [{'a': {'NAND': ['c%', '%d']}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( NOT ( a LIKE 'c%' AND a LIKE '%d' ) )"

    filters = [{'a': {'AND': [['!=', 'AA'], ['!=', 'BB']], 'OR': 'CC%'}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    # python2 sometimes return the other set of conditions first.
    assert (
        formatted_filters == " WHERE ( ( a != 'AA' AND a != 'BB' ) OR a LIKE 'CC%' )"
        or formatted_filters == " WHERE ( a LIKE 'CC%' OR ( a != 'AA' AND a != 'BB' ) )"
    )


@requires_windows
def test_format_filter_bool_op_not():
    filters = [{'my.prop': {'NOT': ['c', 'd']}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( NOT ( my.prop = 'c' OR my.prop = 'd' ) )"

    sampler = WMISampler(
        logger=None, class_name='MyClass', property_names='my.prop', filters=filters, and_props=['my.prop']
    )
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( NOT ( my.prop = 'c' AND my.prop = 'd' ) )"


@requires_windows
def test_format_filter_bool_op_invalid():
    # Falls back to default_bool_op
    filters = [{'my.prop': {'XXX': ['c', 'd']}}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( ( my.prop = 'c' OR my.prop = 'd' ) )"

    sampler = WMISampler(
        logger=None, class_name='MyClass', property_names='my.prop', filters=filters, and_props=['my.prop']
    )
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( ( my.prop = 'c' AND my.prop = 'd' ) )"


@requires_windows
def test_format_filter_wql_op_invalid():
    # Falls back to default_wql_op
    filters = [{'a': [['XXX', 3]]}]
    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=filters)
    formatted_filters = sampler.formatted_filters
    assert formatted_filters == " WHERE ( a = '3' )"


@requires_windows
def test_format_filter_win32_log():
    query = collections.OrderedDict(
        (
            ('TimeGenerated', ('>=', '202056101355.000000+')),
            ('Type', [('=', 'Warning'), ('=', 'Error')]),
            ('SourceName', [('=', 'MSSQLSERVER')]),
        )
    )

    sampler = WMISampler(logger=None, class_name='MyClass', property_names='my.prop', filters=[query])
    formatted_filters = sampler.formatted_filters
    assert (
        formatted_filters == " WHERE ( SourceName = 'MSSQLSERVER' "
        "AND ( Type = 'Warning' OR Type = 'Error' ) AND TimeGenerated >= '202056101355.000000+' )"
    )


@requires_windows
def test_caseinsensitivedict():
    test_dict = CaseInsensitiveDict({})
    key1 = "CAPS_KEY"
    value1 = "CAPS_VALUE"
    test_dict[key1] = value1

    # Assert key is lowercase in CaseInsensitiveDict
    assert CaseInsensitiveDict({key1.lower(): value1}) == test_dict

    # Values do not change
    assert test_dict.get(key1) == value1
    assert test_dict.get(key1.lower()) == value1

    # Copy dict
    test_copy = test_dict.copy()
    assert isinstance(test_copy, CaseInsensitiveDict)

    # Add data to copied dict
    key2 = "DATA"
    value2 = "Dog"
    test_copy[key2] = value2
    assert CaseInsensitiveDict({key1.lower(): value1, key2.lower(): value2}) == test_copy

    assert test_copy.get(key1) == value1
    assert test_copy.get(key1.lower()) == value1
    assert test_copy.get(key2) == value2
    assert test_copy.get(key2.lower()) == value2
