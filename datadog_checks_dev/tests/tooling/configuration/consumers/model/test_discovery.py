# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from ...utils import get_model_consumer, get_spec


class _Model:
    def __init__(self, data):
        self.data = data

    @classmethod
    def model_validate(cls, data, *, context):
        return cls(data)

    def model_dump(self, **kwargs):
        return self.data


def _load_discovery(contents, monkeypatch, **strategy_helpers):
    discovery_utils = ModuleType('datadog_checks.base.utils.discovery')
    discovery_utils.Service = object
    for name, helper in strategy_helpers.items():
        setattr(discovery_utils, name, helper)

    integration_package = ModuleType('datadog_checks.test')
    integration_package.__path__ = []
    config_models = ModuleType('datadog_checks.test.config_models')
    config_models.__path__ = []
    discovery_overrides = ModuleType('datadog_checks.test.config_models.discovery_overrides')
    instance = ModuleType('datadog_checks.test.config_models.instance')
    instance.InstanceConfig = _Model
    shared = ModuleType('datadog_checks.test.config_models.shared')
    shared.SharedConfig = _Model

    integration_package.config_models = config_models
    config_models.discovery_overrides = discovery_overrides
    modules = {
        discovery_utils.__name__: discovery_utils,
        integration_package.__name__: integration_package,
        config_models.__name__: config_models,
        discovery_overrides.__name__: discovery_overrides,
        instance.__name__: instance,
        shared.__name__: shared,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    namespace = {}
    exec(compile(contents, 'discovery.py', 'exec'), namespace)
    return namespace


def test_generated_candidates(monkeypatch):
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_ports
              port_hints:
              - 9090
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors

    candidate_ports = Mock(return_value=[SimpleNamespace(number=9090)])
    candidates = _load_discovery(discovery_contents, monkeypatch, candidate_ports=candidate_ports)['candidates']
    service = SimpleNamespace(host='example.com')

    assert list(candidates(service)) == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:9090/m'}]},
    ]
    candidate_ports.assert_called_once_with(service, [9090])


def test_literal_candidate_values(monkeypatch):
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_ports
              port_hints:
              - 9090
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
                metric_patterns:
                  include:
                  - test.metric.{2}
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
            - name: metric_patterns
              description: words
              value:
                type: object
                additionalProperties: true
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors

    candidate_ports = Mock(return_value=[SimpleNamespace(number=9090)])
    candidates = _load_discovery(discovery_contents, monkeypatch, candidate_ports=candidate_ports)['candidates']
    service = SimpleNamespace(host='example.com')

    assert list(candidates(service)) == [
        {
            'init_config': {},
            'instances': [
                {
                    'endpoint': 'http://example.com:9090/m',
                    'metric_patterns': {'include': ['test.metric.{2}']},
                }
            ],
        }
    ]
    candidate_ports.assert_called_once_with(service, [9090])


def test_from_named_ports(monkeypatch):
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_named_ports
              port_names:
              - metrics
              - http-monitoring
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors

    candidate_ports_by_name = Mock(return_value=[SimpleNamespace(number=8085)])
    candidates = _load_discovery(discovery_contents, monkeypatch, candidate_ports_by_name=candidate_ports_by_name)[
        'candidates'
    ]
    service = SimpleNamespace(host='example.com')

    assert list(candidates(service)) == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:8085/m'}]},
    ]
    candidate_ports_by_name.assert_called_once_with(service, ['metrics', 'http-monitoring'])


def test_local_strategy():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: local:from_app_config
              provides: [svc]
              inputs: {config_path: string}
              config_path: /etc/app.conf
              candidates:
              - endpoint: http://{service.host}:{svc.port}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors
    assert 'from datadog_checks.test.config_models.discovery_strategies import from_app_config' in discovery_contents
    assert "for ctx in from_app_config(service, config_path='/etc/app.conf'):" in discovery_contents
    assert 'InstanceConfig.model_validate(' in discovery_contents
    assert 'from datadog_checks.test.config_models import discovery_overrides' in discovery_contents


def test_override_seam_wired():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_ports
              port_hints: [9090]
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors
    # The override seam is wired even though this integration does not use it:
    # the public candidates() delegates to discovery_overrides.candidates when present.
    assert 'from datadog_checks.test.config_models import discovery_overrides' in discovery_contents
    assert "override = getattr(discovery_overrides, 'candidates', None)" in discovery_contents
    assert 'yield from _generated_candidates(service)' in discovery_contents
    assert 'yield from override(service, default=_generated_candidates)' in discovery_contents


def test_unknown_strategy_clean_error():
    spec = get_spec(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_services
              candidates:
              - endpoint: http://{service.host}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )
    spec.load()

    # An unknown strategy must surface as a clean spec error from validation,
    # never as a traceback or NotImplementedError from the generator.
    assert any('Unsupported strategy `from_services`' in e for e in spec.errors)


def test_custom_files_are_stubbed():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_ports
              port_hints: [9090]
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    files = consumer.render()['test.yaml']
    assert 'discovery_strategies.py' in files
    assert 'discovery_overrides.py' in files
    assert 'candidates(service, default)' in files['discovery_overrides.py'][0]


def test_no_init_config_section():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          discovery:
            strategies:
            - strategy: from_ports
              port_hints:
              - 9090
              candidates:
              - endpoint: http://{service.host}:{port.number}/m
          options:
          - template: instances
            options:
            - name: endpoint
              description: words
              required: true
              value:
                type: string
        """
    )

    discovery_contents, discovery_errors = consumer.render()['test.yaml']['discovery.py']
    assert not discovery_errors
    assert 'SharedConfig' not in discovery_contents
    assert 'from datadog_checks.test.config_models.shared' not in discovery_contents
    assert '    shared = {}' in discovery_contents
