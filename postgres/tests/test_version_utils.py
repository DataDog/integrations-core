# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from mock import MagicMock
from semver import VersionInfo

from datadog_checks.postgres.version_utils import get_version, transform_version

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

    # Test #nightly# style versions
    db.cursor().fetchone.return_value = ['11nightly3']
    _, version = get_version(db)
    assert version == VersionInfo(11, 0, 0, 'nightly.3')


def test_throws_exception_for_unknown_version_format():
    db = MagicMock()
    db.cursor().fetchone.return_value = ['dontKnow']
    with pytest.raises(Exception) as e:
        get_version(db)
    assert e.value.args[0] == "Cannot determine which version is dontKnow"


def test_transform_version():
    version = transform_version('11beta4')
    expected = {
        'version.raw': '11beta4',
        'version.major': 11,
        'version.minor': 0,
        'version.patch': 0,
        'version.release': 'beta.4',
        'version.scheme': 'semver',
    }
    assert expected == version

    version = transform_version('10.0')
    expected = {
        'version.raw': '10.0',
        'version.major': 10,
        'version.minor': 0,
        'version.patch': 0,
        'version.release': None,
        'version.scheme': 'semver',
    }
    assert expected == version

    version = transform_version('10.5.4')
    expected = {
        'version.raw': '10.5.4',
        'version.major': 10,
        'version.minor': 5,
        'version.patch': 4,
        'version.release': None,
        'version.scheme': 'semver',
    }
    assert expected == version
