# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import ensure_parent_dir_exists, path_join, write_file

from .utils import get_spec

pytestmark = pytest.mark.conf


def test_cache():
    spec = get_spec('')
    spec.data = 'test'
    spec.load()
    spec.load()

    assert spec.data == 'test'


def test_invalid_yaml():
    spec = get_spec(
        """
        foo:
          - bar
          baz: oops
        """
    )
    spec.load()

    assert spec.errors[0].startswith('test: Unable to parse the configuration specification')


def test_not_map():
    spec = get_spec('- foo')
    spec.load()

    assert 'test: Configuration specifications must be a mapping object' in spec.errors


def test_no_name():
    spec = get_spec(
        """
        foo:
        - bar
        """
    )
    spec.load()

    assert 'test: Configuration specifications must contain a top-level `name` attribute' in spec.errors


def test_name_not_string():
    spec = get_spec(
        """
        name: 123
        """
    )
    spec.load()

    assert 'test: The top-level `name` attribute must be a string' in spec.errors


def test_no_version():
    spec = get_spec(
        """
        name: foo
        """
    )
    spec.load()

    assert 'test: Configuration specifications must contain a top-level `version` attribute' in spec.errors


def test_version_not_string():
    spec = get_spec(
        """
        name: foo
        version: 123
        """
    )
    spec.load()

    assert 'test: The top-level `version` attribute must be a string' in spec.errors


def test_version_loaded():
    spec = get_spec(
        """
        name: foo
        """,
        version='0.0.0',
    )
    spec.load()

    assert 'test: Configuration specifications must contain a top-level `files` attribute' in spec.errors


def test_no_files():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        """
    )
    spec.load()

    assert 'test: Configuration specifications must contain a top-level `files` attribute' in spec.errors


def test_files_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
          foo: bar
        """
    )
    spec.load()

    assert 'test: The top-level `files` attribute must be an array' in spec.errors


def test_file_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - 5
        - baz
        """
    )
    spec.load()

    assert 'test, file #1: File attribute must be a mapping object' in spec.errors
    assert 'test, file #2: File attribute must be a mapping object' in spec.errors


def test_file_no_name():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - foo: bar
        """
    )
    spec.load()

    assert (
        'test, file #1: Every file must contain a `name` attribute representing the final destination the Agent loads'
    ) in spec.errors


def test_file_name_duplicate():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
        - name: test.yaml
        """
    )
    spec.load()

    assert 'test, file #2: File name `test.yaml` already used by file #1' in spec.errors


def test_example_file_name_duplicate():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
        - name: bar.yaml
          example_name: test.yaml.example
        """
    )
    spec.load()

    assert 'test, file #2: Example file name `test.yaml.example` already used by file #1' in spec.errors


def test_file_name_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: 123
          example_name: test.yaml.example
        """
    )
    spec.load()

    assert 'test, file #1: Attribute `name` must be a string' in spec.errors


def test_example_file_name_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: 123
        """
    )
    spec.load()

    assert 'test, file #1: Attribute `example_name` must be a string' in spec.errors


def test_file_name_standard_incorrect():
    spec = get_spec(
        """
        name: IBM Db2
        version: 0.0.0
        files:
        - name: foo.yaml
        """,
        source='IBM Db2',
    )
    spec.load()

    assert 'IBM Db2, file #1: File name `foo.yaml` should be `ibm_db2.yaml`' in spec.errors


def test_example_file_name_autodiscovery_incorrect():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: auto_conf.yaml
          example_name: test.yaml.example
        """
    )
    spec.load()

    assert 'test, file #1: Example file name `test.yaml.example` should be `auto_conf.yaml`' in spec.errors


def test_example_file_name_standard_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
        """
    )
    spec.load()

    assert spec.data['files'][0]['example_name'] == 'conf.yaml.example'


def test_example_file_name_autodiscovery_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: auto_conf.yaml
        """
    )
    spec.load()

    assert spec.data['files'][0]['example_name'] == 'auto_conf.yaml'


def test_no_options():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
        """
    )
    spec.load()

    assert 'test, test.yaml: Every file must contain an `options` attribute' in spec.errors


def test_sections_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
            foo: bar
        """
    )
    spec.load()

    assert 'test, test.yaml: The `options` attribute must be an array' in spec.errors


def test_section_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - 5
          - baz
        """
    )
    spec.load()

    assert 'test, test.yaml, option #1: Option attribute must be a mapping object' in spec.errors
    assert 'test, test.yaml, option #2: Option attribute must be a mapping object' in spec.errors


def test_section_no_name():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - foo: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, option #1: Every option must contain a `name` attribute' in spec.errors


def test_section_name_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, option #1: Attribute `name` must be a string' in spec.errors


def test_section_name_duplicate():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
          - name: instances
        """
    )
    spec.load()

    assert 'test, test.yaml, option #2: Option name `instances` already used by option #1' in spec.errors


def test_options_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
              foo: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances: The `options` attribute must be an array' in spec.errors


def test_option_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - 5
            - baz
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #1: Option attribute must be a mapping object' in spec.errors
    assert 'test, test.yaml, instances, option #2: Option attribute must be a mapping object' in spec.errors


def test_option_no_name():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - foo: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #1: Every option must contain a `name` attribute' in spec.errors


def test_option_name_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #1: Attribute `name` must be a string' in spec.errors


def test_option_name_duplicate():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: server
            - name: server
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #2: Option name `server` already used by option #1' in spec.errors


def test_option_no_description():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Every option must contain a `description` attribute' in spec.errors


def test_option_description_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `description` must be a string' in spec.errors


def test_option_required_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              required: nope
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `required` must be true or false' in spec.errors


def test_option_required_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['required'] is False


def test_option_hidden_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              hidden: nope
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `hidden` must be true or false' in spec.errors


def test_option_hidden_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['hidden'] is False


def test_option_display_priority_not_integer():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              display_priority: 'abc'
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `display_priority` must be an integer' in spec.errors


def test_option_display_priority_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['display_priority'] == 0


def test_option_deprecation_not_mapping():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              deprecation: nope
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `deprecation` must be a mapping object' in spec.errors


def test_option_deprecation_value_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              deprecation:
                test: 5
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Key `test` for attribute `deprecation` must be a string' in spec.errors


def test_option_deprecation_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['deprecation'] == {}


def test_option_deprecation_ok():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              deprecation:
                test: foo
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['deprecation'] == {'test': 'foo'}


def test_option_metadata_tags_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              metadata_tags: nope
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `metadata_tags` must be an array' in spec.errors


def test_option_metadata_tags_value_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              metadata_tags:
              - 5
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `metadata_tags` must only contain strings' in spec.errors


def test_option_metadata_tags_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['metadata_tags'] == []


def test_option_metadata_tags_ok():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              metadata_tags:
              - test:foo
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['metadata_tags'] == ['test:foo']


def test_option_no_value_nor_options():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
        """
    )
    spec.load()

    assert not spec.errors


def test_option_value_and_options():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              options:
              value:
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: An option cannot contain both `value` and `options` attributes'
    ) in spec.errors


def test_option_value_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
              - foo
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `value` must be a mapping object' in spec.errors


def test_option_secret_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              secret: nope
              value:
                type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `secret` must be true or false' in spec.errors


def test_option_secret_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['secret'] is False


def test_value_no_type():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                foo: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Every value must contain a `type` attribute' in spec.errors


def test_value_type_string_valid_basic():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `type` must be a string' in spec.errors


def test_value_type_string_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['value']['example'] == '<FOO>'


def test_value_type_string_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_string_example_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
                example: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `example` for `type` string must be a string' in spec.errors


def test_value_type_string_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
                example: bar
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_string_pattern_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
                pattern: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `pattern` for `type` string must be a string' in spec.errors


def test_value_type_integer_valid_basic():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_integer_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['value']['example'] == '<FOO>'


def test_value_type_integer_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: integer
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_integer_example_not_number():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                example: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `example` for `type` integer must be a number' in spec.errors


def test_value_type_integer_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                example: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_integer_correct_minimum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                minimum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_integer_incorrect_minimum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                minimum: "5"
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `minimum` for `type` integer must be a number' in spec.errors


def test_value_type_integer_correct_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                maximum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_integer_incorrect_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                maximum: "5"
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `maximum` for `type` integer must be a number' in spec.errors


def test_value_type_integer_correct_minimum_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                minimum: 4
                maximum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_integer_incorrect_minimum_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: integer
                minimum: 5
                maximum: 5
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `maximum` for '
        '`type` integer must be greater than attribute `minimum`'
    ) in spec.errors


def test_value_type_number_valid_basic():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_number_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['value']['example'] == '<FOO>'


def test_value_type_number_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: number
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_number_example_not_number():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                example: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `example` for `type` number must be a number' in spec.errors


def test_value_type_number_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                example: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_number_correct_minimum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                minimum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_number_incorrect_minimum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                minimum: "5"
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `minimum` for `type` number must be a number' in spec.errors


def test_value_type_number_correct_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                maximum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_number_incorrect_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                maximum: "5"
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `maximum` for `type` number must be a number' in spec.errors


def test_value_type_number_correct_minimum_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                minimum: 4
                maximum: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_number_incorrect_minimum_maximum():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                minimum: 5
                maximum: 5
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `maximum` for '
        '`type` number must be greater than attribute `minimum`'
    ) in spec.errors


def test_value_type_boolean_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: boolean
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Every boolean must contain a default `example` attribute' in spec.errors


def test_value_type_boolean_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: boolean
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_boolean_example_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: boolean
                example: "true"
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `example` for `type` boolean must be true or false'
    ) in spec.errors


def test_value_type_boolean_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: boolean
                example: true
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_array_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['options'][0]['value']['example'] == []


def test_value_type_array_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: array
                  items:
                    type: string
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_array_example_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                example: 123
                items:
                  type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `example` for `type` array must be an array' in spec.errors


def test_value_type_array_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                example:
                - foo
                - bar
                items:
                  type: string
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_array_no_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Every array must contain an `items` attribute' in spec.errors


def test_value_type_array_items_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items: 123
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `items` for `type` array must be a mapping object' in spec.errors


def test_value_type_array_unique_items_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                uniqueItems: yup
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `uniqueItems` for `type` array must be true or false'
    ) in spec.errors


def test_value_type_array_correct_min_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                minItems: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_array_incorrect_min_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                minItems: 5.5
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `minItems` for `type` array must be an integer' in spec.errors


def test_value_type_array_correct_max_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                maxItems: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_array_incorrect_max_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                maxItems: 5.5
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `maxItems` for `type` array must be an integer' in spec.errors


def test_value_type_array_correct_min_items_max_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: string
                minItems: 4
                maxItems: 5
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_array_incorrect_min_items_max_items():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: array
                items:
                  type: string
                minItems: 5
                maxItems: 5
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `maxItems` for '
        '`type` array must be greater than attribute `minItems`'
    ) in spec.errors


def test_value_type_object_example_default_no_depth():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
        """
    )
    spec.load()

    assert not spec.errors
    assert spec.data['files'][0]['options'][0]['options'][0]['value']['example'] == {}


def test_value_type_object_example_default_nested():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: array
                items:
                  type: object
        """
    )
    spec.load()

    assert not spec.errors
    assert 'example' not in spec.data['files'][0]['options'][0]['options'][0]['value']['items']


def test_value_type_object_example_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                example: 123
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `example` for `type` object must be a mapping object'
    ) in spec.errors


def test_value_type_object_example_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                example:
                  foo: bar
                items:
                  type: string
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_object_required_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                required: {}
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `required` for `type` object must be an array' in spec.errors


def test_value_type_object_required_empty():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                required: []
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Remove attribute `required` for `type` object if no properties are required'
    ) in spec.errors


def test_value_type_object_required_not_unique():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                required:
                - foo
                - foo
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute `required` for `type` object must be unique'
    ) in spec.errors


def test_value_type_object_properties_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
        """
    )
    spec.load()

    assert not spec.errors
    assert spec.data['files'][0]['options'][0]['options'][0]['value']['properties'] == []


def test_value_type_object_properties_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties: {}
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `properties` for `type` object must be an array' in spec.errors


def test_value_type_object_properties_entry_not_map():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - foo
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Every entry in `properties` for `type` object must be a mapping object'
    ) in spec.errors


def test_value_type_object_properties_entry_no_name():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - type: string
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Every entry in `properties` for `type` object must contain a `name` attribute'
    ) in spec.errors


def test_value_type_object_properties_entry_name_not_string():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - name: 123
                  type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `name` for `type` object must be a string' in spec.errors


def test_value_type_object_properties_valid():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - name: bar
                  type: string
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_object_properties_entry_name_not_unique():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - name: bar
                  type: string
                - name: bar
                  type: string
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute '
        '`properties` for `type` object must have unique names'
    ) in spec.errors


def test_value_type_object_properties_required_not_met():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                properties:
                - name: bar
                  type: string
                required:
                - foo
                - bar
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute `required` '
        'for `type` object must be defined in the `properties` attribute'
    ) in spec.errors


def test_value_type_object_additional_properties_invalid_type():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                additionalProperties: 9000
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `additionalProperties` '
        'for `type` object must be a mapping or set to `true`'
    ) in spec.errors


def test_value_type_object_additional_properties_nested_error():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                additionalProperties:
                  type: object
                  properties:
                  - name: bar
                    type: string
                  required:
                  - foo
                  - bar
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute `required` '
        'for `type` object must be defined in the `properties` attribute'
    ) in spec.errors


def test_value_type_object_additional_properties_nested_ok():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                additionalProperties:
                  type: object
                  properties:
                  - name: foo
                    type: string
                  - name: bar
                    type: string
                  required:
                  - foo
                  - bar
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_object_additional_properties_true_ok():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: object
                additionalProperties: true
        """
    )
    spec.load()

    assert not spec.errors


def test_value_type_unknown():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: custom
        """
    )
    spec.load()

    assert (
        "test, test.yaml, instances, foo: Unknown type `custom`, "
        "valid types are array | boolean | integer | number | object | string" in spec.errors
    )


def test_option_no_section():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: ad_identifiers
            description: words
            value:
              type: array
              items:
                type: string
        """
    )
    spec.load()

    assert not spec.errors


def test_multiple_default():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            options:
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert spec.data['files'][0]['options'][0]['multiple'] is False


def test_multiple_not_boolean():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: foo
            description: words
            multiple: nope
            options:
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, foo: Attribute `multiple` must be true or false' in spec.errors


def test_template_unknown():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
            - template: unknown
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #2: Template `unknown` does not exist' in spec.errors


def test_template_mapping():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
            - template: instances/tags
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert not spec.errors

    options = spec.data['files'][0]['options'][0]['options']
    assert options[0]['name'] == 'foo'
    assert options[1] == {
        'name': 'tags',
        'value': {'example': ['<KEY_1>:<VALUE_1>', '<KEY_2>:<VALUE_2>'], 'type': 'array', 'items': {'type': 'string'}},
        'description': (
            'A list of tags to attach to every metric and service check emitted by this instance.\n'
            '\n'
            'Learn more about tagging at https://docs.datadoghq.com/tagging\n'
        ),
        # Defaults should be post-populated
        'required': False,
        'hidden': False,
        'display_priority': 0,
        'deprecation': {},
        'metadata_tags': [],
        'secret': False,
    }
    assert options[2]['name'] == 'bar'


def test_template_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
            - template: instances/http
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert not spec.errors

    options = spec.data['files'][0]['options'][0]['options']
    option_names = [option['name'] for option in options]
    assert option_names == [
        'foo',
        'proxy',
        'skip_proxy',
        'auth_type',
        'use_legacy_auth_encoding',
        'username',
        'password',
        'ntlm_domain',
        'kerberos_auth',
        'kerberos_cache',
        'kerberos_delegate',
        'kerberos_force_initiate',
        'kerberos_hostname',
        'kerberos_principal',
        'kerberos_keytab',
        'auth_token',
        'aws_region',
        'aws_host',
        'aws_service',
        'tls_verify',
        'tls_use_host_header',
        'tls_ignore_warning',
        'tls_cert',
        'tls_private_key',
        'tls_ca_cert',
        'headers',
        'extra_headers',
        'timeout',
        'connect_timeout',
        'read_timeout',
        'request_size',
        'log_requests',
        'persist_connections',
        'allow_redirects',
        'bar',
    ]


def test_template_array_empty():
    with TempDir() as d:
        template_file = path_join(d, 'empty.yaml')
        ensure_parent_dir_exists(template_file)
        write_file(template_file, '[]')

        spec = get_spec(
            """
            name: foo
            version: 0.0.0
            files:
            - name: test.yaml
              example_name: test.yaml.example
              options:
              - name: instances
                description: words
                options:
                - name: foo
                  description: words
                  value:
                    type: string
                - template: empty
                - name: bar
                  description: words
                  value:
                    type: string
            """,
            template_paths=[d],
        )
        spec.load()

        assert 'test, test.yaml, instances, option #2: Template refers to an empty array' in spec.errors


def test_template_array_primitive():
    with TempDir() as d:
        template_file = path_join(d, 'primitive.yaml')
        ensure_parent_dir_exists(template_file)
        write_file(template_file, '- foo')

        spec = get_spec(
            """
            name: foo
            version: 0.0.0
            files:
            - name: test.yaml
              example_name: test.yaml.example
              options:
              - name: instances
                description: words
                options:
                - name: foo
                  description: words
                  value:
                    type: string
                - template: primitive
                - name: bar
                  description: words
                  value:
                    type: string
            """,
            template_paths=[d],
        )
        spec.load()

        assert 'test, test.yaml, instances, option #2: Template option must be a mapping object' in spec.errors


def test_template_primitive():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: string
            - template: instances/http.proxy.description
            - name: bar
              description: words
              value:
                type: string
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, option #2: Template does not refer to a mapping object nor array' in spec.errors


def test_template_hide_duplicate():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
            - template: instances/http
            - template: instances/jmx
              overrides:
                password.hidden: true
        """
    )
    spec.load()

    assert not spec.errors


def test_value_one_of_with_type():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                type: number
                anyOf: []
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Values must contain either a `type` or `anyOf` attribute, not both'
        in spec.errors
    )


def test_value_one_of_not_array():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                anyOf: bar
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Attribute `anyOf` must be an array' in spec.errors


def test_value_one_of_single_type():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                anyOf:
                - type: string
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: Attribute `anyOf` contains a single type, use the `type` attribute instead'
        in spec.errors
    )


def test_value_one_of_type_not_mapping():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                anyOf:
                - bar
                - {}
        """
    )
    spec.load()

    assert 'test, test.yaml, instances, foo: Type #1 of attribute `anyOf` must be a mapping' in spec.errors


def test_value_one_of_type_recursive_validation_error():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
            options:
            - name: foo
              description: words
              value:
                anyOf:
                - type: string
                - type: object
                  required:
                  - foo
                  - foo
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute `required` for `type` object must be unique'
    ) in spec.errors


def test_value_one_of_type_super_recursive_validation_error():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
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
                      required:
                      - foo
                      - foo
        """
    )
    spec.load()

    assert (
        'test, test.yaml, instances, foo: All entries in attribute `required` for `type` object must be unique'
    ) in spec.errors


def test_value_one_of_type_recursive_validation_success():
    spec = get_spec(
        """
        name: foo
        version: 0.0.0
        files:
        - name: test.yaml
          example_name: test.yaml.example
          options:
          - name: instances
            description: words
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
    spec.load()

    assert not spec.errors
