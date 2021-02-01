# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import mock

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

    assert 'test: The top-level `name` attribute must be a str' in doc.errors


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

    assert 'test: The top-level `files` attribute must be a list' in doc.errors


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


@mock.patch('datadog_checks.dev.tooling.utils.load_manifest', return_value=MOCK_RESPONSE)
def test_file_name_duplicate(_):

    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: README.md
        """
    )
    doc.load()

    assert 'test, file #2: Example file name `README.md` already used by file #1' in doc.errors


def test_file_name_not_string():

    doc = get_doc(
        """
        name: foo
        files:
        - name: 123
        """
    )
    doc.load()

    assert 'test: Docs file #1: Attribute `name` must be a str' in doc.errors


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

    assert 'test: Docs file #1: Attribute `sections` must be a list' in doc.errors


@mock.patch('datadog_checks.dev.tooling.utils.load_manifest', return_value=MOCK_RESPONSE)
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

    assert 'test, README.md, option #1: Option attribute must be a mapping object' in doc.errors
    assert 'test, README.md, option #2: Option attribute must be a mapping object' in doc.errors


def test_section_name_not_string():
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
            - name: 123
        """
    )
    doc.load()

    assert 'test: Docs file #1: Attribute `name` must be a str' in doc.errors


def test_section_name_duplicate():
    doc = get_doc(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: instances
          - name: instances
        """
    )
    doc.load()

    assert 'test, README.md, option #2: Option name `instances` already used by option #1' in doc0.errors
