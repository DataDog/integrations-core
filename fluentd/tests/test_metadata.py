# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.fluentd import Fluentd

from .common import CHECK_NAME

CHECK_ID = 'test:123'


def test_collect_metadata_invalid_binary(datadog_agent, instance):
    instance['fluentd'] = '/bin/does_not_exist'

    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    datadog_agent.assert_metadata(CHECK_ID, {})
    datadog_agent.assert_metadata_count(0)
