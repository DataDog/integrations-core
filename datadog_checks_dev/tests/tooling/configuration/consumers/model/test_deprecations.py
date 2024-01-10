# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ...utils import get_model_consumer


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
                Agent version: 8.0.0
                Migration: do this and that
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
                Agent version: 9.0.0
                Migration: do this and that
              value:
                type: string
        """
    )

    model_definitions = consumer.render()
    files = model_definitions['test.yaml']
    assert len(files) == 5

    _, validators_errors = files['validators.py']
    assert not validators_errors

    _, package_root_errors = files['__init__.py']
    assert not package_root_errors

    deprecation_contents, deprecation_errors = files['deprecations.py']
    assert not deprecation_errors
    assert (
        deprecation_contents
        == """

def shared():
    return {'deprecated': {'Agent version': '8.0.0', 'Migration': 'do this and that'}}


def instance():
    return {'deprecated': {'Agent version': '9.0.0', 'Migration': 'do this and that'}}
"""
    )
