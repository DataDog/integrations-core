# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import importlib
import re
import sys

import datadog_checks
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Port, Service

from ...utils import get_model_consumer, get_spec


def _generate_configs_from_rendered_package(consumer, service, tmp_path, monkeypatch, *, custom_files=None):
    package_name = f'generated_{re.sub(r"\W", "_", tmp_path.name)}'
    spec_file = consumer.spec['files'][0]
    spec_file['name'] = f'{package_name}.yaml'

    rendered_files = consumer.render()[spec_file['name']]
    package_root = tmp_path / 'datadog_checks'
    package_dir = package_root / package_name
    config_models_dir = package_dir / 'config_models'
    config_models_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('')

    custom_files = custom_files or {}
    for file_name, (contents, errors) in rendered_files.items():
        assert not errors
        (config_models_dir / file_name).write_text(custom_files.get(file_name, contents))

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(datadog_checks, '__path__', [str(package_root), *datadog_checks.__path__])
    importlib.invalidate_caches()

    module_name = f'datadog_checks.{package_name}'
    check = type('GeneratedDiscoveryCheck', (AgentCheck,), {'__module__': module_name})
    try:
        return list(check.generate_configs(service))
    finally:
        for imported_module in tuple(sys.modules):
            if imported_module == module_name or imported_module.startswith(f'{module_name}.'):
                sys.modules.pop(imported_module)
        if hasattr(datadog_checks, package_name):
            delattr(datadog_checks, package_name)


def test_generated_candidates_follow_public_discovery_contract(tmp_path, monkeypatch):
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
    service = Service(id='svc', host='example.com', ports=(Port(number=9090),))
    configs = _generate_configs_from_rendered_package(consumer, service, tmp_path, monkeypatch)

    assert configs == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:9090/m'}]},
    ]


def test_literal_candidate_values_follow_public_discovery_contract(tmp_path, monkeypatch):
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
                properties:
                - name: include
                  type: array
                  items:
                    type: string
        """
    )
    service = Service(id='svc', host='example.com', ports=(Port(number=9090),))
    configs = _generate_configs_from_rendered_package(consumer, service, tmp_path, monkeypatch)

    assert configs == [
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


def test_from_named_ports_follows_public_discovery_contract(tmp_path, monkeypatch):
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
    service = Service(
        id='svc',
        host='example.com',
        ports=(
            Port(number=8086, name='http-monitoring'),
            Port(number=9999, name='admin'),
            Port(number=8085, name='metrics'),
        ),
    )
    configs = _generate_configs_from_rendered_package(consumer, service, tmp_path, monkeypatch)

    assert configs == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:8085/m'}]},
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:8086/m'}]},
    ]


def test_local_strategy_follows_public_discovery_contract(tmp_path, monkeypatch):
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
    service = Service(id='svc', host='example.com', ports=())
    configs = _generate_configs_from_rendered_package(
        consumer,
        service,
        tmp_path,
        monkeypatch,
        custom_files={
            'discovery_strategies.py': """
from types import SimpleNamespace


def from_app_config(service, config_path):
    assert service.id == 'svc'
    assert config_path == '/etc/app.conf'
    yield {'svc': SimpleNamespace(port=8123)}
""",
        },
    )

    assert configs == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:8123/m'}]},
    ]


def test_override_seam_follows_public_discovery_contract(tmp_path, monkeypatch):
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
    service = Service(id='svc', host='example.com', ports=(Port(number=9090),))
    configs = _generate_configs_from_rendered_package(
        consumer,
        service,
        tmp_path,
        monkeypatch,
        custom_files={
            'discovery_overrides.py': """
def candidates(service, default):
    for config in default(service):
        config['instances'][0]['endpoint'] += '?source=override'
        yield config
""",
        },
    )

    assert configs == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:9090/m?source=override'}]},
    ]


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

    assert any('Unsupported strategy `from_services`' in error for error in spec.errors)


def test_no_init_config_follows_public_discovery_contract(tmp_path, monkeypatch):
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
    service = Service(id='svc', host='example.com', ports=(Port(number=9090),))
    configs = _generate_configs_from_rendered_package(consumer, service, tmp_path, monkeypatch)

    assert configs == [
        {'init_config': {}, 'instances': [{'endpoint': 'http://example.com:9090/m'}]},
    ]
