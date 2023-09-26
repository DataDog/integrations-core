# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest
from six import PY2

from datadog_checks.win32_event_log import Win32EventLogCheck
from datadog_checks.win32_event_log.legacy import Win32EventLogWMI

from . import common


@pytest.mark.skipif(platform.system() != 'Windows', reason="Test only valid on Windows")
def test_basic_check(aggregator):
    check = Win32EventLogCheck('win32_event_log', {}, [common.INSTANCE])
    check.check(common.INSTANCE)  # First run just initialises timestamp
    check.check(common.INSTANCE)


def test_deprecation_notice(dd_run_check):
    check = Win32EventLogCheck('win32_event_log', {}, [common.INSTANCE])
    dd_run_check(check)
    assert (
        'This version of the check is deprecated and will be removed in a future release. '
        'Set `legacy_mode` to `false` and read about the latest options, such as `query`.'
    ) in check.get_warnings()


@pytest.mark.parametrize('shared_legacy_mode', [None, False, True])
@pytest.mark.parametrize('instance_legacy_mode', [None, False, True])
def test_legacy_mode_select(new_check, shared_legacy_mode, instance_legacy_mode):
    instance = {}
    init_config = None

    if shared_legacy_mode is not None:
        init_config = {'legacy_mode': shared_legacy_mode}
    if instance_legacy_mode is not None:
        instance['legacy_mode'] = instance_legacy_mode

    check = new_check(instance, init_config=init_config)

    # if python2 should alawys choose legacy mode
    if PY2:
        assert type(check) is Win32EventLogWMI
        return

    # if instance option is set it should take precedence
    if instance_legacy_mode:
        assert type(check) is Win32EventLogWMI
        return
    elif instance_legacy_mode is False:
        assert type(check) is Win32EventLogCheck
        return

    # instance option is unset
    assert instance_legacy_mode is None

    # shared/init_config option should apply now
    if shared_legacy_mode:
        assert type(check) is Win32EventLogWMI
        return
    elif shared_legacy_mode is False:
        assert type(check) is Win32EventLogCheck
        return

    # shared/init_config option is unset
    assert shared_legacy_mode is None

    # should default to true for backwards compatibility
    assert type(check) is Win32EventLogWMI
