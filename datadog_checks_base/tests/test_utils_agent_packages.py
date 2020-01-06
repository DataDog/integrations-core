# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.agent.packages import get_datadog_wheels


def test_get_datadog_wheels():
    assert ['checks_tests_helper', 'checks_dev', 'checks_base'] == get_datadog_wheels()
