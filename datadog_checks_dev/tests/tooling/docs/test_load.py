# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from .utils import get_doc

pytestmark = pytest.mark.conf
MOCK_RESPONSE = {'integration_id': 'foo'}


def test_cache():
    doc = get_doc('')
    doc.data = 'test'
    doc.load()
    doc.load()

    assert doc.data == 'test'


def test_invalid_yaml():
    doc = get_doc(
        """
        foo:
          - bar
          baz: oops
        """
    )
    doc.load()

    assert doc.errors[0].startswith('test: Unable to parse the configuration specification')


def test_not_map():
    doc = get_doc('- foo')
    doc.load()

    assert 'test: Docs specifications must be a mapping object' in doc.errors


def test_no_name():
    doc = get_doc(
        """
        foo:
        - bar
        """
    )
    doc.load()

    assert 'test: Docs specifications must include a top-level `name` attribute' in doc.errors


def test_name_not_string():
    doc = get_doc(
        """
        name: 123
        """
    )
    doc.load()

    assert 'test: The top-level `name` attribute must be a string' in doc.errors


def test_no_files():
    doc = get_doc(
        """
        name: foo
        """
    )
    doc.load()

    assert 'test: Docs specifications must include a top-level `files` attribute' in doc.errors


def test_files_not_array():
    doc = get_doc(
        """
        name: foo
        files:
            foo: bar
        """
    )
    doc.load()

    assert 'test: The top-level `files` attribute must be an array' in doc.errors


def test_file_not_map():
    doc = get_doc(
        """
        name: foo
        files:
        - 5
        - baz
        """
    )
    doc.load()

    assert 'test, file #1: File attribute must be a mapping object' in doc.errors
    assert 'test, file #2: File attribute must be a mapping object' in doc.errors


def test_file_no_name():
    doc = get_doc(
        """
        name: foo
        version: 0.0.0
        files:
        - foo: bar
        """
    )
    doc.load()

    assert 'test: Docs file #1: Must include a `name` attribute.' in doc.errors


def test_file_no_section():
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
        """
    )
    doc.load()

    assert 'test: Docs file #1: Must include a `sections` attribute.' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_file_name_duplicate(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
            - name: foo
              header_level: 1
              description: words
        - name: README.md
          sections:
            - name: bar
              header_level: 1
              description: word
        """
    )
    doc.load()

    assert 'test, file #2: File name `README.md` already used by file #1' in doc.errors


def test_file_name_not_string():

    doc = get_doc(
        """
        name: foo
        files:
        - name: 123
        """
    )
    doc.load()

    assert 'test: Docs file #1: Attribute `name` must be a string' in doc.errors


def test_section_not_array():
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
            foo: bar
        """
    )
    doc.load()

    assert 'test: Docs file #1: Attribute `sections` must be an array' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_not_map(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
            - 5
            - baz
        """
    )
    doc.load()

    assert 'test, README.md, section #1: section attribute must be a mapping object' in doc.errors
    assert 'test, README.md, section #2: section attribute must be a mapping object' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_name_not_string(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: 123
        """
    )
    doc.load()

    assert 'test, README.md, section #1: Attribute `name` must be a string' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_name_duplicate(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
          - name: instances
            header_level: 1
            description: words
        """
    )
    doc.load()

    assert 'test, README.md, section #2: section name `instances` already used by section #1' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_name_no_name(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - foo: bar
        """
    )
    doc.load()

    assert 'test, README.md, section #1: Every section must contain a `name` attribute' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_no_header_level(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
        """
    )
    doc.load()

    assert 'test, README.md, section #1: Every section must contain a `header_level` attribute' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_header_level_not_int(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: word
        """
    )
    doc.load()

    assert 'test, README.md, section #1: Attribute `header_level` must be an int' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_section_no_description(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
        """
    )
    doc.load()

    assert 'test, README.md, section #1: Every section must contain a `description` attribute' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_not_array(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
              foo: bar
        """
    )
    doc.load()
    # nested section names don't get carried on to the validator
    assert 'test, README.md, instances: Attribute `sections` must be an array' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_not_map(_):
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - 5
            - baz
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #1: section attribute must be a mapping object' in doc.errors
    assert 'test, README.md, instances, section #2: section attribute must be a mapping object' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_no_name(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - foo: bar
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #1: Every section must contain a `name` attribute' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_name_not_string(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - name: 123
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #1: Attribute `name` must be a string' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_duplicate(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: 1
              description: words
            - name: bar
              header_level: 1
              description: words
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #2: section name `bar` already used by section #1' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_no_description(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: 1
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #1: Every section must contain a `description` attribute' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_header_level_not_int(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: wow
              description: words
        """
    )
    doc.load()

    assert 'test, README.md, instances, section #1: Attribute `header_level` must be an int' in doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_valid_doc(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
        """
    )
    doc.load()

    assert not doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_valid_nested_doc(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: 1
              description: words
        """
    )
    doc.load()

    assert not doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_section_valid_duplicate(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: 1
              description: words
          - name: baz
            header_level: 1
            description: words
            sections:
            - name: bar
              header_level: 1
              description: words
        """
    )
    doc.load()

    assert not doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_bar_valid(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            tab: bar
        """
    )
    doc.load()

    assert not doc.errors


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_link(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: |
                [link][1]

                [1]: datadoghq.com
        """
    )
    doc.load()
    expected_description = '[link](datadoghq.com)'
    assert doc.data['files'][0]['sections'][0]['description'] == expected_description


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_nested_sections_link(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: |
                [link][1]

                [1]: datadoghq.com
            sections:
            - name: bar
              header_level: 1
              description: |
                [foo][1]

                [1]: foo.bar
        """
    )
    doc.load()
    expected_description = '[link](datadoghq.com)'
    expected_nested_description = '[foo](foo.bar)'
    assert doc.data['files'][0]['sections'][0]['description'] == expected_description
    assert doc.data['files'][0]['sections'][0]['sections'][0]['description'] == expected_nested_description


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_append(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            append_text: append
        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['append_text'] == "append"


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_prepend(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            prepend_text: prepend
            description: words
        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['prepend_text'] == "prepend"


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_append_link(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            append_text: |
                [link][1]

                [1]: datadoghq.com
        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['append_text'] == '[link](datadoghq.com)'


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_prepend_link(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            prepend_text: |
                [link][1]

                [1]: datadoghq.com
        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['prepend_text'] == '[link](datadoghq.com)'


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_append_prepend_links(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: |
                [description][1]

                [1]: foo.com
            prepend_text: |
                [prepend][1]

                [1]: bar.com
            append_text: |
                [append][1]

                [1]: baz.com

        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['prepend_text'] == '[prepend](bar.com)'
    assert doc.data['files'][0]['sections'][0]['description'] == '[description](foo.com)'
    assert doc.data['files'][0]['sections'][0]['append_text'] == '[append](baz.com)'


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_sections_prepend_append_empty(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
        """
    )
    doc.load()
    assert doc.data['files'][0]['sections'][0]['prepend_text'] == ""
    assert doc.data['files'][0]['sections'][0]['append_text'] == ""
