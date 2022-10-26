# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest
import win32evtlog

from . import common

pytestmark = [pytest.mark.integration]


@pytest.mark.parametrize('server', ['localhost', '127.0.0.1'])
def test_expected(aggregator, dd_run_check, new_check, instance, report_event, server):
    instance['server'] = server
    check = new_check(instance)
    report_event('message')

    dd_run_check(check)

    aggregator.assert_event(
        'message',
        alert_type='info',
        priority='normal',
        host=check.hostname,
        source_type_name=check.SOURCE_TYPE_NAME,
        aggregation_key=common.EVENT_SOURCE,
        msg_title='Application/{}'.format(common.EVENT_SOURCE),
        tags=[],
    )


def test_recover_from_broken_subscribe(aggregator, dd_run_check, new_check, instance, event_reporter, caplog):
    """
    Test the check can recover from a broken EvtSubscribe handle

    Issue originally surfaced when the event publisher is unregistered while we
    have an EvtSubscribe handle to one of it's channels. This is difficult to test
    here so we mimic it by replacing the subscription handle.
    """
    # Speed up test
    instance['timeout'] = 0.1
    check = new_check(instance)

    # Run check_initializations to create EvtSubscribe
    dd_run_check(check)

    # Create an event
    event_reporter.report('message').join()

    # Mutate the subscription handle so that the check's EvtNext() fails
    check._subscription = None

    # Run the check to initiate the reset
    # Enable debug logging so we see expected error message
    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    # Run the check again to collect the event we missed
    dd_run_check(check)

    # Assert we saw the expected error and we still got an event
    assert 'The handle is invalid' in caplog.text
    aggregator.assert_event('message')


@pytest.mark.parametrize(
    'event_type, level',
    [
        pytest.param(win32evtlog.EVENTLOG_INFORMATION_TYPE, 'info', id='INFORMATION_TYPE'),
        pytest.param(win32evtlog.EVENTLOG_WARNING_TYPE, 'warning', id='WARNING_TYPE'),
        pytest.param(win32evtlog.EVENTLOG_ERROR_TYPE, 'error', id='ERROR_TYPE'),
    ],
)
def test_levels(aggregator, dd_run_check, new_check, instance, report_event, event_type, level):
    check = new_check(instance)
    report_event('foo', event_type=event_type)
    dd_run_check(check)

    aggregator.assert_event('foo', alert_type=level)


def test_event_priority(aggregator, dd_run_check, new_check, instance, report_event):
    instance['event_priority'] = 'low'
    check = new_check(instance)
    report_event('foo')
    dd_run_check(check)

    aggregator.assert_event('foo', priority='low')


def test_event_id(aggregator, dd_run_check, new_check, instance, report_event):
    instance['tag_event_id'] = True
    check = new_check(instance)
    report_event('foo')
    dd_run_check(check)

    aggregator.assert_event('foo', tags=['event_id:{}'.format(common.EVENT_ID)])


def test_included_messages(aggregator, dd_run_check, new_check, instance, report_event):
    instance['included_messages'] = ['bar']
    check = new_check(instance)
    report_event('foo')
    report_event('bar')
    report_event('baz')
    dd_run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event('bar')


def test_excluded_messages(aggregator, dd_run_check, new_check, instance, report_event):
    instance['excluded_messages'] = ['bar']
    check = new_check(instance)
    report_event('foo')
    report_event('bar')
    report_event('baz')
    dd_run_check(check)

    assert len(aggregator.events) == 2
    aggregator.assert_event('foo')
    aggregator.assert_event('baz')


def test_excluded_messages_override(aggregator, dd_run_check, new_check, instance, report_event):
    instance['included_messages'] = ['bar']
    instance['excluded_messages'] = ['bar']
    check = new_check(instance)
    report_event('foo')
    report_event('bar')
    report_event('baz')
    dd_run_check(check)

    assert len(aggregator.events) == 0


def test_custom_query(aggregator, dd_run_check, new_check, instance, report_event):
    instance['query'] = "*[System[Provider[@Name='{}']] and System[(Level=1 or Level=2)]]".format(common.EVENT_SOURCE)
    check = new_check(instance)
    report_event('foo', level='error')
    report_event('bar')
    dd_run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event('foo')


def test_bookmark(aggregator, dd_run_check, new_check, instance, report_event):
    instance['start'] = 'oldest'
    check = new_check(instance)
    report_event('foo')
    report_event('bar')
    dd_run_check(check)

    assert len(aggregator.events) > 1
    aggregator.reset()

    check = new_check(instance)
    dd_run_check(check)

    assert len(aggregator.events) == 0

    report_event('foo')
    dd_run_check(check)

    assert len(aggregator.events) == 1
    aggregator.assert_event('foo')


def test_query_override(aggregator, dd_run_check, new_check, instance, report_event):
    instance['query'] = "*[System[Provider[@Name='foo']]]"
    check = new_check(instance)
    report_event('message')
    dd_run_check(check)

    assert len(aggregator.events) == 0


def test_sid(aggregator, dd_run_check, new_check, instance):
    instance['tag_sid'] = True
    instance['start'] = 'oldest'
    instance['path'] = 'System'
    instance['query'] = "*[System[Provider[@Name='Microsoft-Windows-Kernel-Boot']]]"
    del instance['filters']
    check = new_check(instance)
    dd_run_check(check)

    assert any(
        'sid:NT AUTHORITY\\SYSTEM' in event['tags'] for event in aggregator.events
    ), 'Unable to find any expected `sid` tags'  # no cov
