# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
import logging
from io import StringIO

import pytest

from ddev.monitoring import MonitoringRuntime, console_formatter
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink

PROTECTED = frozenset({'repo', 'commit', 'context'})
HIDDEN = PROTECTED | {'branch', 'pr_number'}


@pytest.fixture
def sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def handler() -> RecordingJsonHandler:
    return RecordingJsonHandler()


@pytest.fixture
def stream() -> StringIO:
    return StringIO()


@pytest.fixture
def console(stream: StringIO) -> logging.Handler:
    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(console_formatter(hidden_fields=HIDDEN))
    return console_handler


def lines(stream: StringIO) -> list[str]:
    return stream.getvalue().splitlines()


def test_component_binding_and_shared_scopes_enrich_logs_and_metrics(
    handler: RecordingJsonHandler, sink: RecordingSink
):
    runtime = MonitoringRuntime(metrics_sink=sink)
    runtime.add_log_handler(handler)
    runtime.set_run_fields(repo='DataDog/integrations-core')
    monitor = runtime.component('planner').bind(operation='dispatch')

    with runtime.component('dispatcher').scope(batch_id='batch-01'):
        monitor.logger.info('Dispatching %s', 'batch')
        monitor.metrics.count('jobs')

    [event] = handler.events
    [record] = sink.records
    assert record.fields == {
        'repo': 'DataDog/integrations-core',
        'component': 'planner',
        'operation': 'dispatch',
        'batch_id': 'batch-01',
    }
    assert event == {**record.fields, 'event': 'Dispatching batch', 'level': 'info'}


def test_resolving_run_fields_affects_future_events_not_emitted_ones(handler: RecordingJsonHandler):
    runtime = MonitoringRuntime()
    runtime.add_log_handler(handler)
    monitor = runtime.component('resolution')
    monitor.logger.info('Resolving run')

    runtime.set_run_fields(commit='head-sha')
    monitor.logger.info('Resolved run')

    assert [event.get('commit') for event in handler.events] == [None, 'head-sha']


@pytest.mark.parametrize('error', [ValueError('boom'), asyncio.CancelledError()])
def test_a_scope_is_reset_even_when_the_block_fails(error):
    runtime = MonitoringRuntime()
    with pytest.raises(type(error)):
        with runtime.context.scope({'batch_id': 'batch-01'}):
            raise error

    assert runtime.context.fields == {}


def test_a_nested_scope_refines_then_restores_the_enclosing_one(sink: RecordingSink):
    runtime = MonitoringRuntime(metrics_sink=sink)
    monitor = runtime.component('test-runner')

    with runtime.context.scope({'batch_id': 'batch-01'}):
        with runtime.context.scope({'job': 'ntp'}):
            monitor.metrics.count('inner')
        monitor.metrics.count('outer')

    [inner, outer] = sink.records
    assert inner.fields['batch_id'] == 'batch-01'
    assert inner.fields['job'] == 'ntp'
    assert 'job' not in outer.fields
    assert outer.fields['batch_id'] == 'batch-01'


def test_a_scope_does_not_cross_runtime_boundaries(sink):
    first = MonitoringRuntime(metrics_sink=sink)
    second = MonitoringRuntime(metrics_sink=sink)

    with first.context.scope({'batch_id': 'batch-01'}):
        first.component('test-runner').metrics.count('scoped')
        second.component('test-runner').metrics.count('unscoped')

    [scoped, unscoped] = sink.records
    assert scoped.fields['batch_id'] == 'batch-01'
    assert 'batch_id' not in unscoped.fields
    assert 'batch_id' not in second.context.fields


def test_concurrent_scopes_do_not_contaminate_each_other(handler, sink):
    runtime = MonitoringRuntime(metrics_sink=sink)
    runtime.add_log_handler(handler)

    async def process(batch_id: str):
        monitor = runtime.component('test-runner')
        with runtime.context.scope({'batch_id': batch_id}):
            await asyncio.sleep(0.01)
            monitor.metrics.count('processed', tags={'tag': batch_id})
            monitor.logger.info('processed')

    async def run_both():
        await asyncio.gather(process('batch-a'), process('batch-b'))

    asyncio.run(run_both())

    records = sink.records_named('processed')
    assert len(records) == 2
    assert {(record.fields['batch_id'], record.tags['tag']) for record in records} == {
        ('batch-a', 'batch-a'),
        ('batch-b', 'batch-b'),
    }
    assert sorted(event['batch_id'] for event in handler.events) == ['batch-a', 'batch-b']


@pytest.mark.parametrize(
    ('scope', 'emit', 'expected_fields', 'expected_tags'),
    [
        (
            {'stage': 'from-scope'},
            lambda monitor: monitor.metrics.count('a record'),
            {'stage': 'from-scope', 'commit': 'actual-head'},
            {},
        ),
        (
            {'stage': 'from-scope'},
            lambda monitor: monitor.metrics.count('a record', stage='from-call'),
            {'stage': 'from-call', 'commit': 'actual-head'},
            {},
        ),
        (
            {'stage': 'from-scope'},
            lambda monitor: monitor.metrics.count('a record', tags={'stage': 'from-tag'}),
            {'stage': 'from-tag', 'commit': 'actual-head'},
            {'stage': 'from-tag'},
        ),
        (
            {'commit': 'wrong-head'},
            lambda monitor: monitor.metrics.count('a record'),
            {'commit': 'actual-head'},
            {},
        ),
        (
            {},
            lambda monitor: monitor.metrics.count('a record', tags={'commit': 'sneaky', 'job': 'ntp'}),
            {'commit': 'actual-head'},
            {'job': 'ntp'},
        ),
        (
            {},
            lambda monitor: monitor.logger.info('a record', commit='other-head', stage='from-log'),
            {'commit': 'actual-head', 'stage': 'from-log'},
            None,
        ),
    ],
    ids=[
        'scope-refines-ordinary',
        'call-beats-scope',
        'tag-beats-scope',
        'scope-cannot-relabel-identity',
        'tag-cannot-relabel-identity',
        'log-call-cannot-relabel-identity',
    ],
)
def test_lower_layers_refine_everything_but_identity(sink, handler, scope, emit, expected_fields, expected_tags):
    runtime = MonitoringRuntime(metrics_sink=sink, protected_fields=PROTECTED)
    runtime.add_log_handler(handler)
    runtime.set_run_fields(repo='DataDog/integrations-core', commit='actual-head', context='pr', stage='from-run')
    monitor = runtime.component('test-runner')

    with runtime.context.scope(scope):
        emit(monitor)

    if expected_tags is None:
        [event] = handler.events
        fields = event
    else:
        [record] = sink.records
        fields = record.fields
        assert record.tags == expected_tags
    assert {key: fields[key] for key in expected_fields} == expected_fields


def test_context_inspection_agrees_with_emitted_records(sink):
    runtime = MonitoringRuntime(metrics_sink=sink, protected_fields=PROTECTED)
    runtime.set_run_fields(commit='actual-head', stage='default')

    with runtime.context.scope({'commit': 'wrong-head', 'stage': 'scoped'}):
        fields = dict(runtime.context.fields)
        runtime.component('test-runner').metrics.count('jobs')

    [record] = sink.records
    assert fields == {'commit': 'actual-head', 'stage': 'scoped'}
    assert record.fields == {**fields, 'component': 'test-runner'}


def test_console_projection_preserves_the_full_event_for_other_handlers(
    stream: StringIO, console: logging.Handler, handler: RecordingJsonHandler
):
    runtime = MonitoringRuntime(console_handler=console)
    runtime.add_log_handler(handler)
    runtime.set_run_fields(repo='DataDog/integrations-core', commit='head-sha', branch='a-branch', pr_number=42)

    with runtime.component('dispatcher').scope(batch_id='batch-01'):
        runtime.component('dispatcher').logger.info('Queued planned batches', batch_count=1)

    [line] = lines(stream)
    assert 'Queued planned batches' in line
    assert 'component=dispatcher' in line
    assert 'batch_id=batch-01' in line
    assert 'batch_count=1' in line
    assert 'repo' not in line
    assert 'commit' not in line

    [event] = handler.events
    assert event == {
        'repo': 'DataDog/integrations-core',
        'commit': 'head-sha',
        'branch': 'a-branch',
        'pr_number': 42,
        'component': 'dispatcher',
        'batch_id': 'batch-01',
        'batch_count': 1,
        'event': 'Queued planned batches',
        'level': 'info',
    }


def test_hidden_metadata_cannot_hide_the_message_or_traceback(
    stream: StringIO, console: logging.Handler, handler: RecordingJsonHandler
):
    console.setFormatter(console_formatter(hidden_fields={'event', 'exception', '_record', '_from_structlog'}))
    runtime = MonitoringRuntime(console_handler=console)
    runtime.add_log_handler(handler)

    try:
        raise ValueError('boom')
    except ValueError:
        runtime.component('dispatcher').logger.exception('dispatch failed')

    rendered = stream.getvalue()
    assert 'dispatch failed' in rendered
    assert 'ValueError: boom' in rendered
    [event] = handler.events
    assert event['event'] == 'dispatch failed'
    assert 'ValueError: boom' in event['exception']


def test_a_runtime_without_handlers_is_silent(capsys: pytest.CaptureFixture[str]):
    runtime = MonitoringRuntime()
    runtime.component('dispatcher').logger.warning('a warning')
    runtime.close()

    assert capsys.readouterr() == ('', '')


def test_repeated_runtimes_do_not_duplicate_or_interfere_with_each_other(stream):
    def handler_for_runtime() -> logging.Handler:
        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(console_formatter())
        return console_handler

    first = MonitoringRuntime(console_handler=handler_for_runtime())
    first.component('dispatcher').logger.info('from the first runtime')
    first.close()

    second = MonitoringRuntime(console_handler=handler_for_runtime())
    second.component('dispatcher').logger.info('from the second runtime')

    assert stream.getvalue().count('from the first runtime') == 1
    assert stream.getvalue().count('from the second runtime') == 1


def test_records_emitted_after_close_are_dropped(stream, console, sink, capsys):
    runtime = MonitoringRuntime(console_handler=console, metrics_sink=sink)
    before = runtime.component('dispatcher')
    before.logger.info('before close')
    before.metrics.count('before')

    runtime.close()
    before.logger.warning('still holding the old view')
    runtime.component('dispatcher').bind(operation='dispatch').logger.warning('derived after close')
    before.metrics.count('after')
    runtime.close()

    rendered = lines(stream)
    assert len(rendered) == 1
    assert 'before close' in rendered[0]
    assert [record.name for record in sink.records] == ['before']
    assert capsys.readouterr().err == ''


def test_closing_the_runtime_leaves_the_callers_stream_open(stream):
    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(console_formatter())
    runtime = MonitoringRuntime(console_handler=console_handler)

    runtime.close()

    stream.write('still usable\n')
    assert stream.getvalue().endswith('still usable\n')
