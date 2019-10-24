# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from mock import MagicMock
from semver import VersionInfo

from datadog_checks.postgres.version_utils import _parse_version, get_version, is_above, transform_version

pytestmark = pytest.mark.unit


def test_get_version():
    """
    Test _get_version() to make sure the check is properly parsing Postgres versions
    """
    db = MagicMock()

    # Test #.#.# style versions
    db.cursor().fetchone.return_value = ['9.5.3']
    _, version = get_version(db)
    assert version == VersionInfo(9, 5, 3)

    # Test #.# style versions
    db.cursor().fetchone.return_value = ['10.2']
    _, version = get_version(db)
    assert version == VersionInfo(10, 2, 0)

    # Test #beta# style versions
    db.cursor().fetchone.return_value = ['11beta3']
    _, version = get_version(db)
    assert version == VersionInfo(11, 0, 0, prerelease='beta.3')

    # Test #rc# style versions
    db.cursor().fetchone.return_value = ['11rc1']
    _, version = get_version(db)
    assert version == VersionInfo(11, 0, 0, prerelease='rc.1')

    # Test #unknown# style versions
    db.cursor().fetchone.return_value = ['11nightly3']
    _, version = get_version(db)
    assert version == VersionInfo(11, 0, 0, 'nightly.3')


def test_is_above():
    """
    Test _is_above() to make sure the check is properly determining order of versions
    """
    # Test major versions
    version = VersionInfo(10, 5, 4)
    assert is_above(version, "9.5.4")
    assert is_above(version, "11.0.0") is False

    # Test minor versions
    assert is_above(version, "10.4.4")
    assert is_above(version, "10.6.4") is False

    # Test patch versions
    assert is_above(version, "10.5.3")
    assert is_above(version, "10.5.5") is False

    # Test same version, _is_above() returns True for greater than or equal to
    assert is_above(version, "10.5.4")

    # Test beta version above
    db = MagicMock()
    db.cursor().fetchone.return_value = ['11beta4']
    _, version = get_version(db)
    assert version > _parse_version('11beta3')

    # Test beta version against official version
    version = VersionInfo(11, 0, 0)
    assert version > _parse_version('11beta3')

    # Test versions of unequal length
    db.cursor().fetchone.return_value = ['10.0']
    _, version = get_version(db)
    assert is_above(version, "10.0.0")
    assert is_above(version, "10.0.1") is False

    # Test return value is not a list
    db.cursor().fetchone.return_value = "foo"
    _, version = get_version(db)
    assert is_above(version, "10.0.0") is False


def test_transform_version():
    version = transform_version('11beta4')
    expected = {
        'version.raw': '11beta4',
        'version.major': 11,
        'version.minor': 0,
        'version.patch': 0,
        'version.build': 'beta.4',
        'version.scheme': 'semver',
    }
    assert expected == version

    version = transform_version('10.0')
    expected = {
        'version.raw': '10.0',
        'version.major': 10,
        'version.minor': 0,
        'version.patch': 0,
        'version.build': None,
        'version.scheme': 'semver',
    }
    assert expected == version

    version = transform_version('10.5.4')
    expected = {
        'version.raw': '10.5.4',
        'version.major': 10,
        'version.minor': 5,
        'version.patch': 4,
        'version.build': None,
        'version.scheme': 'semver',
    }
    assert expected == version
