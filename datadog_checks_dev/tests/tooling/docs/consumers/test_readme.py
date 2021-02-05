# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from ..utils import MOCK_RESPONSE, get_readme_consumer, normalize_readme

pytestmark = [pytest.mark.conf, pytest.mark.conf_consumer]


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_tab_valid(_):

    consumer = get_readme_consumer(
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
    files = consumer.render()
    contents, errors = files['README.md']
    assert not errors
    assert contents == normalize_readme(
        """
        # Agent Check: foo

        <!-- xxx tabs xxx -->
        <!-- xxx tab "bar" xxx -->

        # foo

        words

        <!-- xxz tab xxx -->
        <!-- xxz tabs xxx -->

        """
    )


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_tab_multiple(_):

    consumer = get_readme_consumer(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            tab: bar
          - name: bar
            header_level: 1
            description: words
            tab: baz
        """
    )
    files = consumer.render()
    contents, errors = files['README.md']
    assert not errors
    assert contents == normalize_readme(
        """
        # Agent Check: foo

        <!-- xxx tabs xxx -->
        <!-- xxx tab "bar" xxx -->

        # foo

        words

        <!-- xxz tab xxx -->
        <!-- xxx tab "baz" xxx -->

        # bar

        words

        <!-- xxz tab xxx -->
        <!-- xxz tabs xxx -->

        """
    )


@mock.patch('datadog_checks.dev.tooling.specs.docs.spec.load_manifest', return_value=MOCK_RESPONSE)
def test_tab_multiple_nested(_):

    consumer = get_readme_consumer(
        """
        name: foo
        files:
        - name: README.md
          sections:
          - name: foo
            header_level: 1
            description: words
            tab: bar
            sections:
            - name: nested
              header_level: 1
              description: words
          - name: bar
            header_level: 1
            description: words
            tab: baz
            sections:
            - name: nested
              header_level: 1
              description: words
        """
    )
    files = consumer.render()
    contents, errors = files['README.md']
    assert not errors
    assert contents == normalize_readme(
        """
        # Agent Check: foo

        <!-- xxx tabs xxx -->
        <!-- xxx tab "bar" xxx -->

        # foo

        words

        # nested

        words

        <!-- xxz tab xxx -->
        <!-- xxx tab "baz" xxx -->

        # bar

        words

        # nested

        words

        <!-- xxz tab xxx -->
        <!-- xxz tabs xxx -->

        """
    )
