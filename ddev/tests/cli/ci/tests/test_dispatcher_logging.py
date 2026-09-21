# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher-specific projection of monitoring events onto Datadog logs."""

from __future__ import annotations

import json
import logging

import pytest

from ddev.cli.ci.tests.dispatcher_logging import (
    ci_attributes,
    dispatcher_datadog_formatter,
    project_event,
)
from ddev.monitoring import MonitoringRuntime
from ddev.monitoring.datadog import DatadogLogHandler
from tests.helpers.datadog import FakeLogSubmitter
from tests.helpers.monitoring import RecordingJsonHandler


def test_projection_maps_event_fields_to_datadog_attributes():
    attributes = project_event(
        {
            'event': 'Pull request resolved',
            'level': 'info',
            'repo': 'DataDog/integrations-core',
            'dry_run': False,
            'unlisted_field': 'value',
            'pr_number_missing': None,
        }
    )

    assert attributes['message'] == 'Pull request resolved'
    assert attributes['status'] == 'info'
    assert attributes['service'] == 'ddev'
    assert attributes['ddsource'] == 'dispatcher'
    assert attributes['ddtags'] == 'team:agent-integrations'
    assert attributes['git.repository.id_v2'] == 'github.com/datadog/integrations-core'
    assert attributes['dispatcher.run.dry_run'] == 'false'
    assert attributes['dispatcher.unlisted_field'] == 'value'
    assert 'dispatcher.pr_number_missing' not in attributes


def test_projection_redacts_secret_fields_and_strips_signed_urls_recursively():
    attributes = project_event(
        {
            'event': 'Downloaded https://example.com/artifact?sig=tok#frag done',
            'download_token': 'secret-value',
            'workflow_url': 'https://example.com/run/123?sig=tok#frag',
            'metadata': {
                'headers': {'Authorization': 'Bearer secret'},
                'artifacts': [{'url': 'https://example.com/archive?signature=secret', 'api_key': 'secret-value'}],
            },
        }
    )

    assert attributes['message'] == 'Downloaded https://example.com/artifact done'
    assert attributes['dispatcher.download_token'] == '[REDACTED]'
    assert attributes['dispatcher.batch.workflow.url'] == 'https://example.com/run/123'
    metadata = json.loads(attributes['dispatcher.metadata'])
    assert metadata['headers']['Authorization'] == '[REDACTED]'
    assert metadata['artifacts'] == [{'api_key': '[REDACTED]', 'url': 'https://example.com/archive'}]


def test_ci_attributes_follow_the_github_actions_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('GITHUB_RUN_ID', '9876543210')
    monkeypatch.setenv('GITHUB_RUN_NUMBER', '42')
    monkeypatch.setenv('GITHUB_WORKFLOW', 'dispatch-tests')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'DataDog/integrations-core')
    monkeypatch.setenv('GITHUB_JOB', 'dispatch')
    monkeypatch.delenv('GITHUB_JOB_ID', raising=False)
    monkeypatch.delenv('GITHUB_SERVER_URL', raising=False)

    attributes = ci_attributes()

    assert attributes['ci.provider.name'] == 'github'
    assert attributes['ci.pipeline.id'] == '9876543210'
    assert attributes['ci.pipeline.number'] == '42'
    assert attributes['ci.pipeline.name'] == 'dispatch-tests'
    assert attributes['ci.pipeline.url'] == ('https://github.com/DataDog/integrations-core/actions/runs/9876543210')
    assert attributes['ci.job.name'] == 'dispatch'
    assert 'ci.job.url' not in attributes

    monkeypatch.delenv('GITHUB_RUN_ID')
    assert ci_attributes() == {}


def test_runtime_context_is_delivered_without_changing_the_console_event():
    console = RecordingJsonHandler()
    submitter = FakeLogSubmitter()
    datadog = DatadogLogHandler(api_key='test-api-key', submitter=submitter)
    datadog.setFormatter(dispatcher_datadog_formatter(ci={}))
    runtime = MonitoringRuntime(console_handler=console)
    runtime.add_log_handler(datadog)
    runtime.set_run_fields(repo='DataDog/integrations-core', head_sha='head-sha')

    with runtime.component('test-runner').scope(batch_id='batch-01', run_id=123):
        runtime.component('test-runner').logger.info(
            'Downloading artifact',
            artifact_id=456,
            api_key='secret-value',
        )

    runtime.close()
    datadog.close()

    [event] = console.events
    assert event['component'] == 'test-runner'
    assert event['batch_id'] == 'batch-01'
    assert event['api_key'] == '[REDACTED]'
    assert event['event'] == 'Downloading artifact'

    submitter.assert_log_matches(
        {
            'message': 'Downloading artifact',
            'git.repository.id_v2': 'github.com/datadog/integrations-core',
            'git.commit.sha': 'head-sha',
            'dispatcher.component': 'test-runner',
            'dispatcher.batch.id': 'batch-01',
            'dispatcher.batch.workflow.id': '123',
            'dispatcher.batch.artifact.id': '456',
            'dispatcher.api_key': '[REDACTED]',
        }
    )


def test_console_and_datadog_thresholds_are_independent():
    console = RecordingJsonHandler()
    datadog = RecordingJsonHandler()
    datadog.setLevel(logging.WARNING)
    datadog.setFormatter(dispatcher_datadog_formatter(ci={}))
    runtime = MonitoringRuntime(console_handler=console)
    runtime.add_log_handler(datadog)
    monitor = runtime.component('dispatcher')

    monitor.logger.info('Polling workflow')
    monitor.logger.warning('Artifact download failed', run_id=123)

    assert [event['event'] for event in console.events] == ['Polling workflow', 'Artifact download failed']
    [item] = datadog.events
    assert item['message'] == 'Artifact download failed'
    assert item['status'] == 'warning'
    assert item['dispatcher.batch.workflow.id'] == '123'
