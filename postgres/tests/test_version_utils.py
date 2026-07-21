# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from semver import VersionInfo

from datadog_checks.postgres.util import get_stat_wal_query
from datadog_checks.postgres.version_utils import (
    V14,
    V16,
    V18,
    VersionRange,
    VersionUtils,
    build_versioned_query,
)

pytestmark = pytest.mark.unit


def test_parse_version():
    """
    Test _get_version() to make sure the check is properly parsing Postgres versions
    """
    version = VersionUtils.parse_version('9.5.3')
    assert version == VersionInfo(9, 5, 3)

    # Test #.# style versions
    v10_2 = VersionUtils.parse_version('10.2')
    assert v10_2 == VersionInfo(10, 2, 0)

    v11 = VersionUtils.parse_version('11')
    assert v11 == VersionInfo(11, 0, 0)

    # Test #beta# style versions
    beta11 = VersionUtils.parse_version('11beta3')
    assert beta11 == VersionInfo(11, 0, 0, prerelease='beta.3')

    assert v10_2 < beta11
    assert v11 > beta11

    # Test #rc# style versions
    version = VersionUtils.parse_version('11rc1')
    assert version == VersionInfo(11, 0, 0, prerelease='rc.1')

    # Test #nightly# style versions
    version = VersionUtils.parse_version('11nightly3')
    assert version == VersionInfo(11, 0, 0, 'nightly.3')

    v12_3_tde = VersionUtils.parse_version('12.3_TDE_1.0')
    assert v12_3_tde == VersionInfo(12, 3, 0)


def test_throws_exception_for_unknown_version_format():
    with pytest.raises(Exception) as e:
        VersionUtils.parse_version('dontKnow')
    assert e.value.args[0] == "Cannot determine which version is dontKnow"


def test_transform_version():
    version = VersionUtils.transform_version('11beta4')
    expected = {
        'version.raw': '11beta4',
        'version.major': '11',
        'version.minor': '0',
        'version.patch': '0',
        'version.release': 'beta.4',
        'version.scheme': 'semver',
    }
    assert expected == version

    version = VersionUtils.transform_version('10.0')
    expected = {
        'version.raw': '10.0',
        'version.major': '10',
        'version.minor': '0',
        'version.patch': '0',
        'version.scheme': 'semver',
    }
    assert expected == version

    version = VersionUtils.transform_version('10.5.4')
    expected = {
        'version.raw': '10.5.4',
        'version.major': '10',
        'version.minor': '5',
        'version.patch': '4',
        'version.scheme': 'semver',
    }
    assert expected == version


def test_parse_rds_eol_version():
    version = '11.22-rds.20241121'
    v11_22_rds = VersionUtils.parse_version(version)

    assert v11_22_rds == VersionInfo(11, 22, 20241121)


@pytest.mark.parametrize(
    'version_range, version, expected',
    [
        (VersionRange(), V16, True),
        (VersionRange(min_version=V16), V14, False),
        (VersionRange(min_version=V16), V16, True),
        (VersionRange(min_version=V16), V18, True),
        (VersionRange(max_version=V18), V16, True),
        (VersionRange(max_version=V18), V18, False),
        (VersionRange(min_version=V14, max_version=V18), V14, True),
        (VersionRange(min_version=V14, max_version=V18), V18, False),
    ],
)
def test_version_range_contains(version_range, version, expected):
    """min_version is inclusive, max_version is exclusive, and an open bound never excludes."""
    assert (version in version_range) is expected


def test_build_versioned_query_includes_only_columns_the_version_exposes():
    columns = [
        ('always_expr', {'name': 'always', 'type': 'gauge'}),
        ('added_expr', {'name': 'added', 'type': 'gauge'}, VersionRange(min_version=V16)),
        ('removed_expr', {'name': 'removed', 'type': 'gauge'}, VersionRange(max_version=V18)),
    ]

    on_14 = build_versioned_query('demo', columns, '\n  FROM t\n', V14)
    assert on_14['columns'] == [{'name': 'always', 'type': 'gauge'}, {'name': 'removed', 'type': 'gauge'}]
    assert on_14['query'] == '\nSELECT\n  always_expr,\n  removed_expr\n  FROM t\n'

    on_16 = build_versioned_query('demo', columns, '\n  FROM t\n', V16)
    assert [c['name'] for c in on_16['columns']] == ['always', 'added', 'removed']

    on_18 = build_versioned_query('demo', columns, '\n  FROM t\n', V18)
    assert [c['name'] for c in on_18['columns']] == ['always', 'added']
    assert on_18['name'] == 'demo'


def test_build_versioned_query_requires_a_resolved_version():
    with pytest.raises(ValueError):
        build_versioned_query('demo', [('expr', {'name': 'm', 'type': 'gauge'})], '\n  FROM t\n', None)


def test_get_stat_wal_query_drops_io_timing_columns_on_18():
    """pg_stat_wal lost the wal_write/wal_sync I/O timing columns in PG 18."""
    io_timing = {'wal.write', 'wal.sync', 'wal.write_time', 'wal.sync_time'}

    below_18 = {c['name'] for c in get_stat_wal_query(V14)['columns']}
    assert io_timing <= below_18

    on_18 = {c['name'] for c in get_stat_wal_query(V18)['columns']}
    assert io_timing.isdisjoint(on_18)
    assert 'wal.records' in on_18
