# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import six

from datadog_checks.dev.tooling.requirements import Package, PackageCatalog, read_packages
from datadog_checks.dev.utils import read_file_lines, write_file_lines


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

    p = Package("FOO", "3.0-DEV", 'sys_platform == "WIN32"')
    assert p.name == "foo"
    assert p.version == "3.0-dev"
    assert p.marker == "sys_platform == 'win32'"


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


def test_package__hash__(package):
    """
    Hash value should be the same for different instances having the same
    contents
    """
    other = Package("foo", "3.0", "sys_platform == 'win32'")
    assert package.__hash__() == other.__hash__()


def test_package_catalog_packages(catalog, package):
    assert len(catalog.packages) == 0
    catalog.add_package("a_check", package)
    catalog.add_package("a_check", Package("Aaa", None, None))
    assert len(catalog.packages) == 2
    lst = list(catalog.packages)
    assert lst[0].name == "aaa"
    assert lst[1].name == "foo"


def test_package_catalog_get_package_versions(catalog, package):
    assert catalog.get_package_versions(package) == {}
    catalog.add_package("a_check", package)
    assert len(catalog.get_package_versions(package)) == 1


def test_package_catalog_get_check_packages(catalog, package):
    assert catalog.get_check_packages("a_check") == []
    catalog.add_package("a_check", package)
    assert catalog.get_check_packages("a_check") == [package]
    assert catalog.get_check_packages("another_check") == []


def test_package_catalog_get_package_markers(catalog, package):
    assert catalog.get_package_markers(package) == {}
    catalog.add_package("a_check", package)
    assert len(catalog.get_package_markers(package)) == 1


def test_package_catalog_write_packages(catalog, package, tmp_path):
    out = tmp_path / "out.txt"
    if six.PY2:
        out = str(out)

    catalog.add_package("a_check", package)
    catalog.add_package("a_check", Package("Aaa", "4.0", None))
    catalog.write_packages(out)

    lines = read_file_lines(out)
    assert len(lines) == 2
    assert lines[0] == "aaa==4.0\n"
    assert lines[1] == "foo==3.0; sys_platform == 'win32'\n"


def test_package_catalog_add_package_no_version(catalog, package):
    package.version = ''
    catalog.add_package("a_check", package)
    assert catalog.get_package_versions(package) == {}


def test_package_catalog_add_package_no_marker(catalog, package):
    package.marker = ''
    catalog.add_package("a_check", package)
    assert catalog.get_package_markers(package) == {}


def test_package_catalog_add_package(catalog, package):
    unpinned_foo = Package("foo", None, "sys_platform == 'win32'")
    no_marker_foo = Package("foo", None, None)
    catalog.add_package("a_check", unpinned_foo)
    catalog.add_package("another_check", no_marker_foo)
    catalog.add_package("a_check", package)
    assert len(catalog.packages) == 3


def test_read_packages(catalog, package, tmp_path):
    in_file = tmp_path / "in.txt"
    if six.PY2:
        in_file = str(in_file)

    lines = f'''
        {package}
        bar==4.0
        git+https://github.com/vmware/vsphere-automation-sdk-python@efe345a21b4ab7b346b65e1cb58d56412edd1c10
        git+https://github.com/foo/bar@efe345a#my-branch
        # a comment
           --hash fooBarBaz
    '''
    write_file_lines(in_file, lines)
    result = [str(p) for p in read_packages(in_file)]

    assert result == [
        "foo==3.0; sys_platform == 'win32'",
        'bar==4.0',
        'git+https://github.com/vmware/vsphere-automation-sdk-python@efe345a21b4ab7b346b65e1cb58d56412edd1c10',
        'git+https://github.com/foo/bar@efe345a#my-branch',
    ]
