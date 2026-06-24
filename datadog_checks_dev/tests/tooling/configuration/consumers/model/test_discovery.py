# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ...utils import get_model_consumer, normalize_yaml


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
              - openmetrics_endpoint: http://{service.host}:{port.number}/metrics
          options:
          - template: init_config
            options: []
          - template: instances
            options:
            - name: openmetrics_endpoint
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
        from datadog_checks.test.config_models.instance import InstanceConfig
        from datadog_checks.test.config_models.shared import SharedConfig


        def candidates(service: Service) -> Iterator[dict[str, Any]]:
            shared = SharedConfig().model_dump(mode='json', exclude_none=True)
            # discovery[0]: from_ports
            for port in candidate_ports(service, [9090]):
                ctx = {'port': port}
                instance = InstanceConfig(
                    openmetrics_endpoint='http://{service.host}:{port.number}/metrics'.format(service=service, **ctx),
                ).model_dump(mode='json', exclude_none=True)
                yield {'init_config': shared, 'instances': [instance]}
        """
    )
