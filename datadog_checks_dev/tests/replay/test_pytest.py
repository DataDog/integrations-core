# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from datadog_checks.dev.replay import pytest as replay_pytest


class DummyCheck:
    def __init__(self, name, init_config, instances):
        self.name = name
        self.init_config = init_config
        self.instances = instances


def test_no_agent_defaults_add_http_check_ca_bundle(monkeypatch):
    monkeypatch.setattr(replay_pytest, '_find_default_ca_bundle', lambda: '/tmp/cacert.pem')

    init_config = replay_pytest._apply_no_agent_init_config_defaults('http_check', {})

    assert init_config == {'ca_certs': '/tmp/cacert.pem'}


def test_no_agent_defaults_preserve_configured_http_check_ca_bundle(monkeypatch):
    monkeypatch.setattr(replay_pytest, '_find_default_ca_bundle', lambda: '/tmp/cacert.pem')

    init_config = replay_pytest._apply_no_agent_init_config_defaults('http_check', {'ca_certs': '/custom.pem'})

    assert init_config == {'ca_certs': '/custom.pem'}


def test_build_check_instances_passes_init_config_and_no_agent_defaults(monkeypatch):
    monkeypatch.setattr(replay_pytest, '_find_default_ca_bundle', lambda: '/tmp/cacert.pem')

    checks = replay_pytest.build_check_instances(DummyCheck, [{'url': 'https://example.com'}], 'http_check')

    assert checks[0].init_config == {'ca_certs': '/tmp/cacert.pem'}
    assert checks[0].instances == [{'url': 'https://example.com'}]
