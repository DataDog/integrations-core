# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('option', ['included_messages', 'excluded_messages'])
def test_invalid_message_filter_regular_expression(dd_run_check, new_check, instance, option):
    instance[option] = ['\\1']
    check = new_check(instance)

    with pytest.raises(
        Exception,
        match='Error compiling pattern for option `{}`: invalid group reference 1 at position 1'.format(option),
    ):
        dd_run_check(check)


def test_legacy_v2_params_notice(dd_run_check, new_check, instance):
    instance['dd_security_events'] = 'high'
    check = new_check(instance)
    dd_run_check(check)
    assert (
        'dd_security_events config option is ignored when running legacy_mode_v2. Please remove it'
    ) in check.get_warnings()


def test_legacy_v2_params_defaults_dont_notice(dd_run_check, new_check, instance):
    check = new_check(instance)
    dd_run_check(check)
    assert not check.get_warnings()
