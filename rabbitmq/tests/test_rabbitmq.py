# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest


@pytest.mark.usefixtures('dd_environment')
def test_metadata(check, instance, aggregator, version_metadata):
    check.check_id = 'test:123'

    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        check.check(instance)
        for name, value in version_metadata.items():
            m.assert_any_call('test:123', name, value)

        assert m.call_count == len(version_metadata)
