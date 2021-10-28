# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, INSTANCE


@pytest.mark.parametrize(
    'stdout, stderr, expect_metadata_count',
    [('gunicorn (version 19.9.0)', '', 5), ('', 'gunicorn (version 19.9.0)', 5), ('foo bar', '', 0), ('', '', 0)],
)
def test_collect_metadata_parsing_matching(aggregator, datadog_agent, stdout, stderr, expect_metadata_count):
    """Test all metadata collection code paths"""
    check = GUnicornCheck(CHECK_NAME, {}, [INSTANCE])
    check.check_id = 'test:123'

    with mock.patch('datadog_checks.gunicorn.gunicorn.get_subprocess_output', return_value=(stdout, stderr, 0)):
        check.check(INSTANCE)

    datadog_agent.assert_metadata_count(expect_metadata_count)
