# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from mock import MagicMock
from semver import VersionInfo

from datadog_checks.postgres.version_utils import get_version

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


def test_throws_exception_for_unknown_version_format():
    db = MagicMock()
    db.cursor().fetchone.return_value = ['dontKnow']
    with pytest.raises(Exception) as e:
        get_version(db)
    assert e.value.args[0] == "Cannot determine which version is dontKnow"
