# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.avi_vantage import AviVantageCheck


def test_missing_url(dd_run_check):
    instance = {}
    check = AviVantageCheck('avi_vantage', {}, [instance])
    with pytest.raises(Exception, match=r'avi_controller_url'):
        dd_run_check(check)


def test_bad_entity(dd_run_check):
    instance = {"avi_controller_url": "foo", "entities": ["foo"]}
    check = AviVantageCheck('avi_vantage', {}, [instance])
    with pytest.raises(
        Exception,
        match=(
            "InstanceConfig`:\nentities -> 1\n"
            "  Input should be 'controller', 'pool', 'serviceengine' or 'virtualservice'"
        ),
    ):
        dd_run_check(check)
