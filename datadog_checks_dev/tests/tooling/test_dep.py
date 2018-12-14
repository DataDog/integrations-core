# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import six

from datadog_checks.dev.tooling.dep import Package, PackageCatalog
from datadog_checks.dev.utils import read_file_lines


@pytest.fixture
def package():
    return Package("foo", "3.0", "sys_platform == 'win32'")


@pytest.fixture
def catalog():
    return PackageCatalog()


def test_package_init(package):
    assert package.name == "foo"
    assert package.version == "3.0"
    assert package.marker == "sys_platform == 'win32'"

    with pytest.raises(ValueError):
        p = Package("", "3.0", "marker")
    p = Package("FOO", None, None)
    assert p.name == "foo"
    assert p.version == ""
    assert p.marker == ""


def test_package__str__(package):
    assert "{}".format(package) == "foo==3.0; sys_platform == 'win32'"


def test_package_rich_comparison(package):
    assert (package != package) is False
    assert (package == package) is True
    assert (package < package) is False
    assert (package > package) is False

    other = Package("Aaa", "4.0", None)
    assert (package == other) is False
    assert (package > other) is True
    assert (package < other) is False

    other = Package("foo", "4.0", None)
    assert (package == other) is False
    assert (package > other) is False
    assert (package < other) is True

    assert (package == 42) is False
    assert (package != 42) is True

    if six.PY3:
        with pytest.raises(TypeError):
            package < 42
    else:
        assert (package < 42) is True


def test_package__hash__(package):
    """
    Hash value should be the same for different instances having the same
    contents
    """
    other = Package("foo", "3.0", "sys_platform == 'win32'")
    assert package.__hash__() == other.__hash__()


def test_package_catalog_errors(catalog):
    assert len(catalog.errors) is 0
    catalog._errors.append("foo")
    assert len(catalog.errors) is 1
    assert catalog.errors.pop() == "foo"


def test_package_catalog_packages(catalog, package):
    assert len(catalog.packages) is 0
    catalog.add_package("a_check", package)
    catalog.add_package("a_check", Package("Aaa", None, None))
    assert len(catalog.packages) is 2
    lst = list(catalog.packages)
    assert lst[0].name == "aaa"
    assert lst[1].name == "foo"


def test_package_catalog_get_package_versions(catalog, package):
    assert catalog.get_package_versions(package) == {}
    catalog.add_package("a_check", package)
    assert len(catalog.get_package_versions(package)) is 1


def test_package_catalog_get_check_packages(catalog, package):
    assert catalog.get_check_packages("a_check") == []
    catalog.add_package("a_check", package)
    assert catalog.get_check_packages("a_check") == [package]
    assert catalog.get_check_packages("another_check") == []


def test_package_catalog_get_package_markers(catalog, package):
    assert catalog.get_package_markers(package) == {}
    catalog.add_package("a_check", package)
    assert len(catalog.get_package_markers(package)) is 1


def test_package_catalog_write_packages(catalog, package, tmp_path):
    out = tmp_path / "out.txt"
    if six.PY2:
        out = str(out)

    catalog.add_package("a_check", package)
    catalog.add_package("a_check", Package("Aaa", "4.0", None))
    catalog.write_packages(out)

    lines = read_file_lines(out)
    assert len(lines) is 2
    assert lines[0] == "aaa==4.0\n"
    assert lines[1] == "foo==3.0; sys_platform == 'win32'\n"


def test_package_catalog_add_package(catalog, package):
    unpinned_foo = Package("foo", None, "sys_platform == 'win32'")
    no_marker_foo = Package("foo", None, None)
    catalog.add_package("a_check", unpinned_foo)
    catalog.add_package("a_check", package)
    catalog.add_package("another_check", no_marker_foo)
    assert len(catalog.errors) is 3
    assert catalog.errors[0] == "Unpinned dependency `foo` in the `a_check` check."
    assert catalog.errors[1] == "Unpinned dependency `foo` in the `another_check` check."
    exp = "Multiple environment marker definitions for `foo` in checks ['another_check'] and ['a_check', 'a_check']."
    assert catalog.errors[2] == exp
