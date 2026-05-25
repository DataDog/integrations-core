# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import sys
import types

import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.dev.replay.adapters.requests import build_get_record, install_replay_session_get
from datadog_checks.dev.replay.diff import diff_outputs
from datadog_checks.dev.replay.normalize import normalize_output
from datadog_checks.dev.replay.pytest import infer_check_class


class ExampleCheck(AgentCheck):
    def check(self, instance):
        pass


def test_infer_check_class_from_module_exports(monkeypatch):
    module = types.ModuleType('datadog_checks.example_replay')
    module.__all__ = ['__version__', 'ExampleCheck']
    module.__version__ = '1.0.0'
    module.ExampleCheck = ExampleCheck
    monkeypatch.setitem(sys.modules, 'datadog_checks.example_replay', module)

    assert infer_check_class('example_replay') is ExampleCheck


def test_normalize_output_sorts_metrics_and_tags():
    output = {
        'metrics': [
            {'name': 'z.metric', 'type': 0, 'value': 2, 'tags': ['b:2', 'a:1'], 'hostname': '', 'device': None},
            {'name': 'a.metric', 'type': 0, 'value': 1, 'tags': ['z:9'], 'hostname': '', 'device': None},
        ],
        'service_checks': [],
        'events': [],
        'event_platform_events': {},
    }

    normalized = normalize_output(output)

    assert [metric['name'] for metric in normalized['metrics']] == ['a.metric', 'z.metric']
    assert normalized['metrics'][1]['tags'] == ['a:1', 'b:2']


def test_diff_outputs_reports_added_and_removed_metric_records():
    old = {
        'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1, 'tags': ['a:1']}],
        'service_checks': [],
        'events': [],
    }
    new = {
        'metrics': [{'name': 'example.metric', 'type': 0, 'value': 2, 'tags': ['a:1']}],
        'service_checks': [],
        'events': [],
    }

    diff = diff_outputs(old, new)

    assert diff['changed'] is True
    assert diff['collections']['metrics']['removed'] == old['metrics']
    assert diff['collections']['metrics']['added'] == new['metrics']


def test_requests_replay_fixture_miss_on_wrong_url(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record('http://example.test/metrics', 'metric 1\n')]) + '\n')
    install_replay_session_get(monkeypatch, fixture_path)

    with pytest.raises(AssertionError, match='does not match'):
        requests.Session().get('http://example.test/other')


def test_requests_replay_fixture_miss_when_records_exhausted(monkeypatch, tmp_path):
    fixture_path = tmp_path / 'capture.json'
    fixture_path.write_text(json.dumps([build_get_record('http://example.test/metrics', 'metric 1\n')]) + '\n')
    install_replay_session_get(monkeypatch, fixture_path)

    requests.Session().get('http://example.test/metrics')
    with pytest.raises(AssertionError, match='No recorded HTTP response'):
        requests.Session().get('http://example.test/metrics')
