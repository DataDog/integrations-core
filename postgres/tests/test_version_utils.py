# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from mock import MagicMock
from semver import VersionInfo

from datadog_checks.postgres.version_utils import get_version, is_above

pytestmark = pytest.mark.unit


def test_get_version():
    """
    Test _get_version() to make sure the check is properly parsing Postgres versions
    """
    db = MagicMock()

    # Test #.#.# style versions
    db.cursor().fetchone.return_value = ['9.5.3']
    assert get_version(db) == VersionInfo(9, 5, 3)

    # Test #.# style versions
    db.cursor().fetchone.return_value = ['10.2']
    assert get_version(db) == VersionInfo(10, 2, 0)

    # Test #beta# style versions
    db.cursor().fetchone.return_value = ['11beta3']
    assert get_version(db) == VersionInfo(11, -1, 3)

    # Test #rc# style versions
    db.cursor().fetchone.return_value = ['11rc1']
    assert get_version(db) == VersionInfo(11, -1, 1)

    # Test #nightly# style versions
    db.cursor().fetchone.return_value = ['11nightly3']
    assert get_version(db) == VersionInfo(11, -1, 3)

    # Test #unknown# style versions
    db.cursor().fetchone.return_value = ['dontKnow']
    assert get_version(db) == 'dontKnow'


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
    version = get_version(db)
    assert version > VersionInfo(11, -1, 3)

    # Test beta version against official version
    version = VersionInfo(11, 0, 0)
    assert version > VersionInfo(11, -1, 3)

    # Test versions of unequal length
    db.cursor().fetchone.return_value = ['10.0']
    version = get_version(db)
    assert is_above(version, "10.0.0")
    assert is_above(version, "10.0.1") is False

    # Test return value is not a list
    db.cursor().fetchone.return_value = "foo"
    version = get_version(db)
    assert is_above(version, "10.0.0") is False
