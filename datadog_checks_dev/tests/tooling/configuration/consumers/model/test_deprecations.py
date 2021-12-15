# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ...utils import get_model_consumer, normalize_yaml

pytestmark = [pytest.mark.conf, pytest.mark.conf_consumer, pytest.mark.conf_consumer_model]


def test():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          options:
          - template: init_config
            options:
            - name: timeout
              description: words
              value:
                type: number
            - name: deprecated
              description: words
              deprecation:
                Release: 8.0.0
                Migration: |
                  do this
                  and that
              value:
                type: string
          - template: instances
            options:
            - name: text
              description: words
              value:
                type: string
            - name: deprecated
              description: words
              deprecation:
                Release: 9.0.0
                Migration: |
                  do this
                  and that
              value:
                type: string
        """
    )

    model_definitions = consumer.render()
    assert len(model_definitions) == 1

    files = model_definitions['test.yaml']
    assert len(files) == 6

    validators_contents, validators_errors = files['validators.py']
    assert not validators_errors

    package_root_contents, package_root_errors = files['__init__.py']
    assert not package_root_errors

    deprecation_contents, deprecation_errors = files['deprecations.py']
    assert not deprecation_errors
    assert deprecation_contents == normalize_yaml(
        """def shared():
            return {'deprecated': {'Release': '8.0.0', 'Migration': 'do this\nand that\n'}}

        def instance():
            return {'deprecated': {'Release': '9.0.0', 'Migration': 'do this\nand that\n'}}
        """
    )
