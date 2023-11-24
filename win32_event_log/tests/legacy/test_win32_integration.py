# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest
from six import PY2

from datadog_checks.base import ConfigurationError
from datadog_checks.base.errors import SkipInstanceError
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
@pytest.mark.parametrize('shared_legacy_mode_v2', [None, False, True])
@pytest.mark.parametrize('instance_legacy_mode_v2', [None, False, True])
def test_legacy_mode_select(
    new_check, shared_legacy_mode, instance_legacy_mode, shared_legacy_mode_v2, instance_legacy_mode_v2
):
    instance = {}
    init_config = {}
    if shared_legacy_mode is not None:
        init_config['legacy_mode'] = shared_legacy_mode
    if instance_legacy_mode is not None:
        instance['legacy_mode'] = instance_legacy_mode
    if shared_legacy_mode_v2 is not None:
        init_config['legacy_mode_v2'] = shared_legacy_mode_v2
    if instance_legacy_mode_v2 is not None:
        instance['legacy_mode_v2'] = instance_legacy_mode_v2

    print(init_config, instance)

    legacy_mode_opts = [
        # legacy mode set by init_config
        shared_legacy_mode and instance_legacy_mode is None,
        # legacy_mode set by instance
        instance_legacy_mode,
    ]
    legacy_mode_v2_opts = [
        # legacy mode v2 set by init_config
        shared_legacy_mode_v2 and instance_legacy_mode_v2 is None,
        # legacy_mode v2 set by instance
        instance_legacy_mode_v2,
    ]
    # default to legacy_mode=True if other opts are unset
    if not any(legacy_mode_v2_opts):
        selected_default = shared_legacy_mode is not False and instance_legacy_mode is None
    else:
        selected_default = False

    # Must only set a single mode
    if any(legacy_mode_opts) and any(legacy_mode_v2_opts):
        with pytest.raises(ConfigurationError, match="are both true"):
            check = new_check(instance, init_config=init_config)
        return

    # legacy_mode_v2 is not supported on Python2
    if PY2 and any(legacy_mode_v2_opts):
        with pytest.raises(ConfigurationError, match="not supported on Python2"):
            check = new_check(instance, init_config=init_config)
        return

    # Must raise SkipInstanceError if both options are False
    if not selected_default and not any(legacy_mode_opts) and not any(legacy_mode_v2_opts):
        with pytest.raises(SkipInstanceError):
            check = new_check(instance, init_config=init_config)
        return

    # Check constructor must now succeed without raising an exception
    check = new_check(instance, init_config=init_config)

    # if instance option is set it should take precedence
    if instance_legacy_mode:
        assert type(check) is Win32EventLogWMI
        return
    elif instance_legacy_mode_v2:
        assert type(check) is Win32EventLogCheck
        return

    # shared/init_config option should apply now, instance option must be None
    if shared_legacy_mode and instance_legacy_mode is None:
        assert type(check) is Win32EventLogWMI
        return
    elif shared_legacy_mode_v2 and instance_legacy_mode_v2 is None:
        assert type(check) is Win32EventLogCheck
        return

    # No option was selected, confirm the default type
    if selected_default:
        assert type(check) is Win32EventLogWMI
        return

    # We should have covered all the cases above and should not reach here
    raise AssertionError("Case was not tested")
