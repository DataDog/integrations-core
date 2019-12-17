# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.dev.tooling.configuration.consumers.example import DESCRIPTION_LINE_LENGTH_LIMIT

from ..utils import get_example_consumer, normalize_yaml

pytestmark = [pytest.mark.conf, pytest.mark.conf_consumer]


def test_option_no_section():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: ad_identifiers
            overrides:
              value.example:
              - httpd
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param ad_identifiers - list of strings - required
        ## A list of container identifiers that will be used by autodiscovery to identify
        ## which container the check should be run against. For more information, see:
        ## https://docs.datadoghq.com/agent/autodiscovery/ad_identifiers/
        #
        ad_identifiers:
          - httpd
        """
    )


def test_section_with_option():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
            - name: bar
              description: bar words
              value:
                type: number
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

            ## @param bar - number - optional
            ## bar words
            #
            # bar: <BAR>
        """
    )


def test_section_with_option_hidden():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
            - name: bar
              description: bar words
              hidden: true
              value:
                type: number
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>
        """
    )


def test_section_hidden():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            hidden: true
            options:
            - name: foo
              description: foo words
              value:
                type: string
          - template: instances
            options:
            - name: bar
              description: bar words
              required: true
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance will be scheduled independent of the others.
        #
        instances:

            ## @param bar - string - required
            ## bar words
            #
          - bar: <BAR>
        """
    )


def test_section_example():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: foo words
            example: here
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## foo words
        #
        # foo: here
        """
    )


@pytest.mark.skipif(PY2, reason='Dictionary key order is not guaranteed in Python 2')
def test_section_example_indent():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
          - template: logs
            example:
            - type: file
              path: /var/log/apache2/access.log
              source: apache
              service: apache
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Log Section
        ##
        ## type - required - Type of log input source (tcp / udp / file / windows_event)
        ## port / path / channel_path - required - Set port if type is tcp or udp.
        ##                                         Set path if type is file.
        ##                                         Set channel_path if type is windows_event.
        ## service - required - Name of the service that generated the log
        ## source  - required - Attribute that defines which Integration sent the logs
        ## sourcecategory - optional - Multiple value attribute. Used to refine the source attribute
        ## tags - optional - Add tags to the collected logs
        ##
        ## Discover Datadog log collection: https://docs.datadoghq.com/logs/log_collection/
        #
        # logs:
        #   - type: file
        #     path: /var/log/apache2/access.log
        #     source: apache
        #     service: apache
        """
    )


def test_section_multiple_required():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
          - template: instances
            options:
            - name: bar
              description: bar words
              required: true
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance will be scheduled independent of the others.
        #
        instances:

            ## @param bar - string - required
            ## bar words
            #
          - bar: <BAR>
        """
    )


def test_section_multiple_no_required():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
          - template: instances
            options:
            - name: bar
              description: bar words
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance will be scheduled independent of the others.
        #
        instances:

          -
            ## @param bar - string - optional
            ## bar words
            #
            # bar: <BAR>
        """
    )


def test_section_multiple_required_not_first():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              value:
                type: string
          - template: instances
            options:
            - name: foo
              description: foo words
              value:
                type: string
            - name: bar
              description: bar words
              required: true
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, _ = files['test.yaml.example']
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance will be scheduled independent of the others.
        #
        instances:

          -
            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

            ## @param bar - string - required
            ## bar words
            #
            bar: <BAR>
        """
    )


def test_option_object_type():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: object
              example:
                bar: it
              properties:
              - name: bar
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - mapping - optional
        ## words
        #
        # foo:
        #   bar: it
        """
    )


def test_option_array_type_array():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: array
              example:
              - - 0
                - 1
              - - 2
                - 3
              items:
                type: array
                items:
                  type: integer
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - list of lists - optional
        ## words
        #
        # foo:
        #   - - 0
        #     - 1
        #   - - 2
        #     - 3
        """
    )


def test_option_array_type_object():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: array
              example:
              - bar: it
              items:
                type: object
                properties:
                - name: bar
                  type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - list of mappings - optional
        ## words
        #
        # foo:
        #   - bar: it
        """
    )


def test_option_boolean_type():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: boolean
              example: true
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - boolean - optional - default: true
        ## words
        #
        # foo: true
        """
    )


def test_option_number_type():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: number
              example: 5
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - number - optional - default: 5
        ## words
        #
        # foo: 5
        """
    )


def test_option_number_type_default():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: number
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - number - optional
        ## words
        #
        # foo: <FOO>
        """
    )


def test_option_string_type_not_default():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            value:
              type: string
              example: something
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional - default: something
        ## words
        #
        # foo: something
        """
    )


def test_section_description_length_limit():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: {}
            options:
            - name: bar
              description: words
              value:
                type: string
        """.format(
            'a' * DESCRIPTION_LINE_LENGTH_LIMIT
        )
    )

    files = consumer.render()
    _, errors = files['test.yaml.example']
    assert 'Description line length of section `foo` was over the limit by 3 characters' in errors


def test_option_description_length_limit():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: {}
            value:
              type: string
        """.format(
            'a' * DESCRIPTION_LINE_LENGTH_LIMIT
        )
    )

    files = consumer.render()
    _, errors = files['test.yaml.example']
    assert 'Description line length of option `foo` was over the limit by 3 characters' in errors


@pytest.mark.skipif(PY2, reason='Dictionary key order is not guaranteed in Python 2')
def test_deprecation():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options:
            - name: foo
              description: foo words
              deprecation:
                Release: 8.0.0
                Migration: |
                  do this
                  and that
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            ##
            ## <<< DEPRECATED >>>
            ##
            ## Release: 8.0.0
            ## Migration: do this
            ##            and that
            #
            # foo: <FOO>
        """
    )


def test_template():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: instances
            options:
            - name: foo
              description: words
              required: true
              value:
                type: string
            - template: instances/global
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance will be scheduled independent of the others.
        #
        instances:

            ## @param foo - string - required
            ## words
            #
          - foo: <FOO>

            ## @param min_collection_interval - number - optional - default: 15
            ## This changes the collection interval of the check. For more information, see:
            ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
            #
            # min_collection_interval: 15

            ## @param empty_default_hostname - boolean - optional - default: false
            ## This forces the check to send metrics with no hostname.
            ##
            ## This is useful for cluster-level checks.
            #
            # empty_default_hostname: false
        """
    )


def test_no_options():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: init_config
            options: []
          - template: instances
            options: []
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here will be available to all instances.
        #
        init_config:

        ## Every instance will be scheduled independent of the others.
        #
        instances:

          - {}
        """
    )
