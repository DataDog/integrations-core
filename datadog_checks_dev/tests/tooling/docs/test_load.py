# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .utils import get_doc

pytestmark = pytest.mark.conf


def test_cache():
    spec = get_doc('')
    spec.data = 'test'
    spec.load()
    spec.load()

    assert spec.data == 'test'


def test_invalid_yaml():
    spec = get_doc(
        """
        foo:
          - bar
          baz: oops
        """
    )
    spec.load()

    assert spec.errors[0].startswith('test: Unable to parse the configuration specification')


def test_not_map():
    spec = get_doc('- foo')
    spec.load()

    assert 'test: Docs specifications must be a mapping object' in spec.errors


def test_no_name():
    spec = get_doc(
        """
        foo:
        - bar
        """
    )
    spec.load()

    assert 'test: Docs specifications must contain a top-level `name` attribute' in spec.errors
