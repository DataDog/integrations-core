# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.couchbase import Couchbase


def test_camel_case_to_joined_lower():
    couchbase = Couchbase('couchbase', {}, {})

    CAMEL_CASE_TEST_PAIRS = {
        'camelCase': 'camel_case',
        'FirstCapital': 'first_capital',
        'joined_lower': 'joined_lower',
        'joined_Upper1': 'joined_upper1',
        'Joined_upper2': 'joined_upper2',
        'Joined_Upper3': 'joined_upper3',
        '_leading_Underscore': 'leading_underscore',
        'Trailing_Underscore_': 'trailing_underscore',
        'DOubleCAps': 'd_ouble_c_aps',
        '@@@super--$$-Funky__$__$$%': 'super_funky',
    }

    for test_input, expected_output in CAMEL_CASE_TEST_PAIRS.items():
        test_output = couchbase.camel_case_to_joined_lower(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output)


def test_extract_seconds_value():
    couchbase = Couchbase('couchbase', {}, {})

    EXTRACT_SECONDS_TEST_PAIRS = {
        '3.45s': 3.45,
        '12ms': .012,
        '700.5us': .0007005,
        u'733.364\u00c2s': .000733364,
        '0': 0,
    }

    for test_input, expected_output in EXTRACT_SECONDS_TEST_PAIRS.items():
        test_output = couchbase.extract_seconds_value(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output)
