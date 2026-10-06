# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from clickhouse_connect.driver.exceptions import DatabaseError, OperationalError

from datadog_checks.clickhouse import utils


@pytest.mark.unit
class TestErrorSanitizer:
    def test_clean(self):
        assert utils.ErrorSanitizer.clean('error..  Stack trace:  \n\n') == 'error.'

    def test_scrub(self):
        sanitizer = utils.ErrorSanitizer('foo')

        assert sanitizer.scrub('foobar') == '**********bar'

    def test_scrub_no_password(self):
        sanitizer = utils.ErrorSanitizer('')

        assert sanitizer.scrub('foobar') == 'foobar'


@pytest.mark.unit
@pytest.mark.parametrize(
    ['version', 'expected'],
    [
        ('25', [25]),
        ('25.1', [25, 1]),
        ('25.1.2', [25, 1, 2]),
        ('25.1.2.3', [25, 1, 2, 3]),
        ('25.3.8.30001.altinityfips', [25, 3, 8, 30001]),
    ],
)
def test_parse_version(version: str, expected: list[int]):
    assert utils.parse_version(version) == expected


ACCESS_DENIED_PREFIX = 'Code: 497. DB::Exception: datadog: Not enough privileges. To execute this query, '


@pytest.mark.unit
@pytest.mark.parametrize(
    ['probe', 'error', 'expected'],
    [
        pytest.param(
            utils.TopologyProbe.CLUSTER_MACRO,
            DatabaseError(
                f"{ACCESS_DENIED_PREFIX}it's necessary to have the grant SELECT(substitution) ON system.macros. "
                "(ACCESS_DENIED) (version 24.8.4.13 (official build))"
            ),
            utils.ProbeError(utils.ProbeErrorKind.DENIED, ('SELECT ON system.macros',)),
            id='denied-column-grant',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError(f"{ACCESS_DENIED_PREFIX}it's necessary to have grant REMOTE ON *.*. (ACCESS_DENIED)"),
            utils.ProbeError(utils.ProbeErrorKind.DENIED, (utils.REMOTE_GRANT,)),
            id='denied-remote-legacy-wording',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError(f"{ACCESS_DENIED_PREFIX}it's necessary to have the grant READ ON REMOTE. (ACCESS_DENIED)"),
            utils.ProbeError(utils.ProbeErrorKind.DENIED, (utils.REMOTE_GRANT,)),
            id='denied-read-on-remote',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError(
                f"{ACCESS_DENIED_PREFIX}it's necessary to have the grant CREATE TEMPORARY TABLE, REMOTE ON *.*. "
                "(ACCESS_DENIED)"
            ),
            utils.ProbeError(utils.ProbeErrorKind.DENIED, ('CREATE TEMPORARY TABLE ON *.*', utils.REMOTE_GRANT)),
            id='denied-several-privileges',
        ),
        pytest.param(
            utils.TopologyProbe.CLOUD_MODE,
            DatabaseError('Code: 497. DB::Exception: datadog: Not enough privileges. (ACCESS_DENIED)'),
            utils.ProbeError(utils.ProbeErrorKind.DENIED, ('SELECT ON system.settings',)),
            id='denied-without-a-named-grant',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError("Code: 701. DB::Exception: Requested cluster 'prod' not found. (CLUSTER_DOESNT_EXIST)"),
            utils.ProbeError(utils.ProbeErrorKind.UNKNOWN_CLUSTER),
            id='unknown-cluster',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError("Code: 170. DB::Exception: Requested cluster 'prod' not found. (BAD_GET)"),
            utils.ProbeError(utils.ProbeErrorKind.UNKNOWN_CLUSTER),
            id='unknown-cluster-legacy',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            DatabaseError(
                'Code: 516. DB::Exception: Received from node-b:9000. DB::Exception: datadog: Authentication failed: '
                'password is incorrect, or there is no user with such name. (AUTHENTICATION_FAILED)'
            ),
            utils.ProbeError(utils.ProbeErrorKind.AUTHENTICATION_FAILED),
            id='authentication-failed-on-a-remote-node',
        ),
        pytest.param(
            utils.TopologyProbe.NODES,
            OperationalError('Error HTTPConnectionPool(host=ch, port=8123): Read timed out. executing HTTP request'),
            utils.ProbeError(utils.ProbeErrorKind.TIMEOUT),
            id='timeout',
        ),
        pytest.param(
            utils.TopologyProbe.CLUSTER_NAME,
            OperationalError('Error [Errno 111] Connection refused executing HTTP request attempt 1'),
            utils.ProbeError(utils.ProbeErrorKind.CONNECTION),
            id='connection',
        ),
        pytest.param(
            utils.TopologyProbe.CLUSTER_NAME,
            OperationalError('Code: 60. DB::Exception: Unknown table expression identifier. (UNKNOWN_TABLE)'),
            utils.ProbeError(utils.ProbeErrorKind.ERROR),
            id='server-error-after-retry',
        ),
    ],
)
def test_classify_probe_error(probe: str, error: Exception, expected: utils.ProbeError):
    classified = utils.classify_probe_error(probe, error)

    assert (classified.kind, classified.grants) == (expected.kind, expected.grants)
