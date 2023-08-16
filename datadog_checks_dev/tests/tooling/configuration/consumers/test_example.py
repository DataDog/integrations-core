# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.dev.tooling.configuration.consumers.example import DESCRIPTION_LINE_LENGTH_LIMIT

from ..utils import get_example_consumer, normalize_yaml


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
        ## A list of container identifiers that are used by Autodiscovery to identify
        ## which container the check should be run against. For more information, see:
        ## https://docs.datadoghq.com/agent/guide/ad_identifiers/
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
        ## All options defined here are available to all instances.
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
        ## All options defined here are available to all instances.
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
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## @param bar - string - required
            ## bar words
            #
          - bar: <BAR>
        """
    )


def test_section_with_option_display_priority():
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
            - name: fourth
              description: fourth words
              display_priority: -5
              value:
                type: string
            - name: fifth
              description: fifth words
              display_priority: -50
              value:
                type: string
            - name: third
              description: third words
              # default display_priority: 0
              value:
                type: string
            - name: first
              description: first words
              display_priority: 100
              value:
                type: number
            - name: second
              description: second words
              display_priority: 10
              value:
                type: number
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param first - number - optional
            ## first words
            #
            # first: <FIRST>

            ## @param second - number - optional
            ## second words
            #
            # second: <SECOND>

            ## @param third - string - optional
            ## third words
            #
            # third: <THIRD>

            ## @param fourth - string - optional
            ## fourth words
            #
            # fourth: <FOURTH>

            ## @param fifth - string - optional
            ## fifth words
            #
            # fifth: <FIFTH>
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Log Section
        ##
        ## type - required - Type of log input source (tcp / udp / file / windows_event).
        ## port / path / channel_path - required - Set port if type is tcp or udp.
        ##                                         Set path if type is file.
        ##                                         Set channel_path if type is windows_event.
        ## source  - required - Attribute that defines which integration sent the logs.
        ## encoding - optional - For file specifies the file encoding. Default is utf-8. Other
        ##                       possible values are utf-16-le and utf-16-be.
        ## service - optional - The name of the service that generates the log.
        ##                      Overrides any `service` defined in the `init_config` section.
        ## tags - optional - Add tags to the collected logs.
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


@pytest.mark.skipif(PY2, reason='Dictionary key order is not guaranteed in Python 2')
def test_section_example_indent_required():
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
            required: true
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Log Section
        ##
        ## type - required - Type of log input source (tcp / udp / file / windows_event).
        ## port / path / channel_path - required - Set port if type is tcp or udp.
        ##                                         Set path if type is file.
        ##                                         Set channel_path if type is windows_event.
        ## source  - required - Attribute that defines which integration sent the logs.
        ## encoding - optional - For file specifies the file encoding. Default is utf-8. Other
        ##                       possible values are utf-16-le and utf-16-be.
        ## service - optional - The name of the service that generates the log.
        ##                      Overrides any `service` defined in the `init_config` section.
        ## tags - optional - Add tags to the collected logs.
        ##
        ## Discover Datadog log collection: https://docs.datadoghq.com/logs/log_collection/
        #
        logs:
          - type: file
            path: /var/log/apache2/access.log
            source: apache
            service: apache
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance is scheduled independently of the others.
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance is scheduled independently of the others.
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            # foo: <FOO>

        ## Every instance is scheduled independently of the others.
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


def test_option_string_type_not_default_example_default_value_none():
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
              display_default: null
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional
        ## words
        #
        # foo: something
        """
    )


def test_option_string_type_not_default_example_default_value_null():
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
              display_default: null
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional
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


def test_option_description_length_limit_with_noqa():
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
              example: something
        """.format(
            'a' * DESCRIPTION_LINE_LENGTH_LIMIT + ' /noqa'
        )
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional - default: something
        ## {}
        #
        # foo: something
        """.format(
            'a' * DESCRIPTION_LINE_LENGTH_LIMIT
        )
    )


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
                Agent version: 8.0.0
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
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            ##
            ## <<< DEPRECATED >>>
            ##
            ## Agent version: 8.0.0
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
        ## Every instance is scheduled independently of the others.
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


def test_template_recursion():
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
            - template: instances/default
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## @param foo - string - required
            ## words
            #
          - foo: <FOO>

            ## @param tags - list of strings - optional
            ## A list of tags to attach to every metric and service check emitted by this instance.
            ##
            ## Learn more about tagging at https://docs.datadoghq.com/tagging
            #
            # tags:
            #   - <KEY_1>:<VALUE_1>
            #   - <KEY_2>:<VALUE_2>

            ## @param service - string - optional
            ## Attach the tag `service:<SERVICE>` to every metric, event, and service check emitted by this integration.
            ##
            ## Overrides any `service` defined in the `init_config` section.
            #
            # service: <SERVICE>

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

            ## @param metric_patterns - mapping - optional
            ## A mapping of metrics to include or exclude, with each entry being a regular expression.
            ##
            ## Metrics defined in `exclude` will take precedence in case of overlap.
            #
            # metric_patterns:
            #   include:
            #   - <INCLUDE_REGEX>
            #   exclude:
            #   - <EXCLUDE_REGEX>
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
        ## All options defined here are available to all instances.
        #
        init_config:

        ## Every instance is scheduled independently of the others.
        #
        instances:

          - {}
        """
    )


def test_compact_example():
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
              compact_example: true
              example:
              - - 0
                - 1
              - foo
              - foo: bar
                bar: baz
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
        #   - [0, 1]
        #   - "foo"
        #   - {foo: bar, bar: baz}
        #   - [2, 3]
        """
    )


def test_compact_example_long_line():
    long_str = "This string is very long and has 50 chars in it !!"
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
              compact_example: true
              example:
                - - {0}
                  - {0}
                  - {0}
                  - {0}
              items:
                type: array
                items:
                  type: string
        """.format(
            long_str
        )
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
        #   - [{0}, {0}, {0}, {0}]
        """.format(
            long_str
        )
    )


def test_compact_example_nested():
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
              value:
                type: array
                compact_example: true
                example:
                - - 0
                  - 1
                - foo
                - foo: bar
                  bar: baz
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
        ## Every instance is scheduled independently of the others.
        #
        instances:

          -
            ## @param foo - list of lists - optional
            ## words
            #
            # foo:
            #   - [0, 1]
            #   - "foo"
            #   - {foo: bar, bar: baz}
            #   - [2, 3]
        """
    )


def test_option_default_example_override_null():
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
              display_default: null
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional
        ## words
        #
        # foo: something
        """
    )


def test_option_default_example_override_string():
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
              display_default: bar
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional - default: bar
        ## words
        #
        # foo: something
        """
    )


def test_option_default_example_override_non_string():
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
              display_default:
                foo: [bar, baz]
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## @param foo - string - optional - default: {'foo': ['bar', 'baz']}
        ## words
        #
        # foo: something
        """
    )


def test_enabled_override_required():
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
              required: false
              enabled: true
              value:
                type: string
          - template: instances
            options:
            - name: bar
              description: bar words
              required: true
              enabled: false
              value:
                type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## All options defined here are available to all instances.
        #
        init_config:

            ## @param foo - string - optional
            ## foo words
            #
            foo: <FOO>

        ## Every instance is scheduled independently of the others.
        #
        instances:

          -
            ## @param bar - string - required
            ## bar words
            #
            # bar: <BAR>
        """
    )


def test_option_multiple_types():
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
              value:
                anyOf:
                - type: string
                - type: array
                  items:
                    type: string
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

          -
            ## @param foo - string or list of strings - optional
            ## words
            #
            # foo: <FOO>
        """
    )


def test_option_multiple_types_nested():
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
              value:
                anyOf:
                - type: string
                - type: array
                  items:
                    anyOf:
                    - type: string
                    - type: object
                      properties:
                      - name: foo
                        type: string
                      required:
                      - foo
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

          -
            ## @param foo - string or (list of string or mapping) - optional
            ## words
            #
            # foo: <FOO>
        """
    )


def test_option_multiple_instances_defined():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: instances
            multiple_instances_defined: true
            options:
            - name: instance_1
              description: Description of the first instance
              options:
              - name: foo
                description: words
                value:
                  type: string
            - name: instance_2
              description: |
                Description of the second instance
                Multiple lines
              options:
              - name: bar
                description: description
                value:
                  type: string

        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## Description of the first instance
          -
            ## @param foo - string - optional
            ## words
            #
            # foo: <FOO>

            ## Description of the second instance
            ## Multiple lines
          -
            ## @param bar - string - optional
            ## description
            #
            # bar: <BAR>
        """
    )


def test_parent_option_disabled():
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
            - name: enabled_option
              required: true
              description: Description of enabled option
              value:
                type: boolean
                example: true
            - name: parent_option
              description: Description of parent option
              options:
              - name: sub_option_1
                description: words
                value:
                  type: boolean
                  example: true
              - name: sub_option_2
                description: words
                value:
                  type: string
                  example: foo.bar_none
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## @param enabled_option - boolean - required
            ## Description of enabled option
            #
          - enabled_option: true

            ## Description of parent option
            #
            # parent_option:

                ## @param sub_option_1 - boolean - optional - default: true
                ## words
                #
                # sub_option_1: true

                ## @param sub_option_2 - string - optional - default: foo.bar_none
                ## words
                #
                # sub_option_2: foo.bar_none
        """
    )


def test_parent_option_enabled():
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
            - name: enabled_option
              required: true
              description: Description of enabled option
              value:
                type: boolean
                example: true
            - name: parent_option
              enabled: true
              description: Description of parent option
              options:
              - name: enabled_sub_option
                enabled: true
                description: words
                value:
                  type: boolean
                  example: true
              - name: disabled_sub_option
                description: words
                value:
                  type: string
                  example: foo.bar_none
        """
    )

    files = consumer.render()
    contents, errors = files['test.yaml.example']
    assert not errors
    assert contents == normalize_yaml(
        """
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## @param enabled_option - boolean - required
            ## Description of enabled option
            #
          - enabled_option: true

            ## Description of parent option
            #
            parent_option:

                ## @param enabled_sub_option - boolean - optional - default: true
                ## words
                #
                enabled_sub_option: true

                ## @param disabled_sub_option - string - optional - default: foo.bar_none
                ## words
                #
                # disabled_sub_option: foo.bar_none
        """
    )


def test_multi_instances_w_nested_options():
    consumer = get_example_consumer(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - template: instances
            multiple_instances_defined: true
            options:
            - name: Instance A
              description: Instance A Example
              options:
              - name: option_w_options
                enabled: true
                description: Option with options description
                options:
                - name: sub_option_1
                  required: true
                  description: Sub_option_1 description
                  value:
                    type: boolean
                    example: true
                - name: sub_option_2
                  description: Sub_option_2 description
                  value:
                    type: string
                    example: foobar
            - name: Instance B
              description: Instance B Example
              options:
              - name: option_3
                description: Option_3 description
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
        ## Every instance is scheduled independently of the others.
        #
        instances:

            ## Instance A Example
          -
            ## Option with options description
            #
            option_w_options:

                ## @param sub_option_1 - boolean - required
                ## Sub_option_1 description
                #
                sub_option_1: true

                ## @param sub_option_2 - string - optional - default: foobar
                ## Sub_option_2 description
                #
                # sub_option_2: foobar

            ## Instance B Example
          -
            ## @param option_3 - boolean - optional - default: true
            ## Option_3 description
            #
            # option_3: true
        """
    )
