# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import importlib
from textwrap import dedent

from datadog_checks.dev.tooling.configuration import ConfigSpec
from datadog_checks.dev.tooling.configuration.consumers import ExampleConsumer

config_module = importlib.import_module('datadog_checks.dev.tooling.commands.validate.config')

AUTO_CONF_SPEC = """
name: Test
version: 0.0.0
files:
- name: auto_conf.yaml
  options:
  - template: ad_identifiers
    overrides:
      value.example:
      - test
  - template: auto_conf/discovery
"""


def get_spec(text):
    spec = ConfigSpec(dedent(text).lstrip(), source='test')
    spec.load()
    assert not spec.errors
    return spec


def render_discovery_block(spec):
    contents, errors = ExampleConsumer(spec.data).render()['auto_conf.yaml']
    assert not errors
    return contents


def test_metrics_prefix_added_when_prefix_diverges_from_check_name(monkeypatch):
    monkeypatch.setattr(config_module, 'get_metric_prefix', lambda check: 'zookeeper.')

    spec = get_spec(AUTO_CONF_SPEC)
    config_module.apply_discovery_metrics_prefix(spec.data, 'zk')

    assert 'discovery:\n  metrics_prefix: zookeeper\n' in render_discovery_block(spec)


def test_metrics_prefix_omitted_when_prefix_matches_check_name(monkeypatch):
    monkeypatch.setattr(config_module, 'get_metric_prefix', lambda check: 'test.')

    spec = get_spec(AUTO_CONF_SPEC)
    config_module.apply_discovery_metrics_prefix(spec.data, 'test')

    assert 'discovery: {}\n' in render_discovery_block(spec)


def test_metrics_prefix_omitted_when_no_prefix_is_declared(monkeypatch):
    monkeypatch.setattr(config_module, 'get_metric_prefix', lambda check: '')

    spec = get_spec(AUTO_CONF_SPEC)
    config_module.apply_discovery_metrics_prefix(spec.data, 'test')

    assert 'discovery: {}\n' in render_discovery_block(spec)


def test_metrics_prefix_does_not_override_explicit_spec_example(monkeypatch):
    monkeypatch.setattr(config_module, 'get_metric_prefix', lambda check: 'zookeeper.')

    spec = get_spec(
        """
        name: Test
        version: 0.0.0
        files:
        - name: auto_conf.yaml
          options:
          - template: ad_identifiers
            overrides:
              value.example:
              - test
          - template: auto_conf/discovery
            overrides:
              discovery.example:
                metrics_prefix: custom
        """
    )
    config_module.apply_discovery_metrics_prefix(spec.data, 'zk')

    assert 'discovery:\n  metrics_prefix: custom\n' in render_discovery_block(spec)
