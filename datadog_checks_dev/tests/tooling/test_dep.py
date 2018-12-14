# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import six

from datadog_checks.dev.tooling.dep import Package


@pytest.fixture
def package():
    return Package("foo", "3.0", "sys_platform == 'win32'")


def test_package_init(package):
    assert package.name == "foo"
    assert package.version == "3.0"
    assert package.marker == "sys_platform == 'win32'"


def test_package__str__(package):
    assert "{}".format(package) == "foo==3.0; sys_platform == 'win32'"


def test_package__lt__(package):
    assert (package < package) is False
    if six.PY3:
        with pytest.raises(TypeError):
            package < 42
    else:
        assert (package < 42) is True
    other = Package("aaa", "3.0", "")
    assert other < package
    other = Package("foo", "2.0", "sys_platform == 'win32'")
    assert other < package


def test_package__eq__(package):
    assert (package == package) is True
    other = Package("aaa", "3.0", "")
    assert (package == other) is False
    assert (package == 42) is False


def test_package__neq__(package):
    assert (package != package) is False
    other = Package("aaa", "3.0", "")
    assert (package != other) is True
    assert (package != 42) is True


def test_package__hash__(package):
    """
    Hash value should be the same for different instances having the same
    contents
    """
    other = Package("foo", "3.0", "sys_platform == 'win32'")
    assert package.__hash__() == other.__hash__()
