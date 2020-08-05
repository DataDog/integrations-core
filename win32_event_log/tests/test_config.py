# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.unit]


def test_no_path(dd_run_check, new_check, instance):
    del instance['path']
    check = new_check(instance)

    with pytest.raises(Exception, match='You must select a `path`.'):
        dd_run_check(check)


def test_invalid_start_option(dd_run_check, new_check, instance):
    instance['start'] = 'soon'
    check = new_check(instance)

    with pytest.raises(Exception, match='Option `start` must be one of: now, oldest'):
        dd_run_check(check)


def test_invalid_event_priority(dd_run_check, new_check, instance):
    instance['event_priority'] = 'important'
    check = new_check(instance)

    with pytest.raises(Exception, match='Option `event_priority` can only be either `normal` or `low`.'):
        dd_run_check(check)


@pytest.mark.parametrize('option', ['included_messages', 'excluded_messages'])
def test_invalid_message_filter_regular_expression(dd_run_check, new_check, instance, option):
    instance[option] = ['\\1']
    check = new_check(instance)

    with pytest.raises(
        Exception,
        match='Error compiling pattern for option `{}`: invalid group reference 1 at position 1'.format(option),
    ):
        dd_run_check(check)


def test_filters_not_map(dd_run_check, new_check, instance):
    instance['filters'] = 'foo'
    check = new_check(instance)

    with pytest.raises(Exception, match='The `filters` option must be a mapping.'):
        dd_run_check(check)


def test_filter_value_not_array(dd_run_check, new_check, instance):
    instance['filters'] = {'foo': 'bar'}
    check = new_check(instance)

    with pytest.raises(Exception, match='Value for event filter `foo` must be an array.'):
        dd_run_check(check)


def test_unknown_auth_type(dd_run_check, new_check, instance):
    instance['server'] = 'foo'
    instance['auth_type'] = 'foo'
    check = new_check(instance)

    with pytest.raises(Exception, match='Invalid `auth_type`, must be one of: default, negotiate, kerberos, ntlm'):
        dd_run_check(check)
