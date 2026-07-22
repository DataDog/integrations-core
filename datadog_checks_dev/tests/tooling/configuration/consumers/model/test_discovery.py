# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ...utils import get_model_consumer, get_spec, normalize_yaml


def test():
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

    model_definitions = consumer.render()
    files = model_definitions['test.yaml']

    discovery_contents, discovery_errors = files['discovery.py']
    assert not discovery_errors
    assert discovery_contents == normalize_yaml(
        """
        from __future__ import annotations

        from collections.abc import Iterator
        from typing import Any

        from datadog_checks.base.utils.discovery import Service, candidate_ports
        from datadog_checks.test.config_models import discovery_overrides
        from datadog_checks.test.config_models.instance import InstanceConfig
        from datadog_checks.test.config_models.shared import SharedConfig


        def _generated_candidates(service: Service) -> Iterator[dict[str, Any]]:
            shared = SharedConfig.model_validate({}, context={'configured_fields': frozenset()}).model_dump(
                by_alias=True, mode='json', exclude_none=True
            )
            # discovery[0]: from_ports
            for port in candidate_ports(service, [9090]):
                ctx = {'port': port}
                instance_data = {
                    'endpoint': 'http://{service.host}:{port.number}/m'.format(service=service, **ctx),
                }
                instance = InstanceConfig.model_validate(
                    instance_data, context={'configured_fields': frozenset(instance_data)}
                ).model_dump(by_alias=True, mode='json', exclude_none=True)
                yield {'init_config': shared, 'instances': [instance]}


        def candidates(service: Service) -> Iterator[dict[str, Any]]:
            override = getattr(discovery_overrides, 'candidates', None)
            if override is None:
                yield from _generated_candidates(service)
            else:
                yield from override(service, default=_generated_candidates)
        """
    )


def test_literal_candidate_values():
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
    assert discovery_contents == normalize_yaml(
        """
        from __future__ import annotations

        from collections.abc import Iterator
        from typing import Any

        from datadog_checks.base.utils.discovery import Service, candidate_ports
        from datadog_checks.test.config_models import discovery_overrides
        from datadog_checks.test.config_models.instance import InstanceConfig
        from datadog_checks.test.config_models.shared import SharedConfig


        def _generated_candidates(service: Service) -> Iterator[dict[str, Any]]:
            shared = SharedConfig.model_validate({}, context={'configured_fields': frozenset()}).model_dump(
                by_alias=True, mode='json', exclude_none=True
            )
            # discovery[0]: from_ports
            for port in candidate_ports(service, [9090]):
                ctx = {'port': port}
                instance_data = {
                    'endpoint': 'http://{service.host}:{port.number}/m'.format(service=service, **ctx),
                    'metric_patterns': {'include': ['test.metric.{2}']},
                }
                instance = InstanceConfig.model_validate(
                    instance_data, context={'configured_fields': frozenset(instance_data)}
                ).model_dump(by_alias=True, mode='json', exclude_none=True)
                yield {'init_config': shared, 'instances': [instance]}


        def candidates(service: Service) -> Iterator[dict[str, Any]]:
            override = getattr(discovery_overrides, 'candidates', None)
            if override is None:
                yield from _generated_candidates(service)
            else:
                yield from override(service, default=_generated_candidates)
        """
    )


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
