# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import mock
import pytest

from datadog_checks.gitlab_runner import GitlabRunnerCheck

from . import common


@pytest.mark.unit
@pytest.mark.parametrize(
    'test_case, timeout_config, expected_timeout',
    [
        ("legacy config", {"connect_timeout": 8, "receive_timeout": 7}, (8, 7)),
        ("new config", {"connect_timeout": 8, "read_timeout": 7}, (8, 7)),
        ("default timeout", {}, (5, 15)),
    ],
)
def test_timeout(test_case, timeout_config, expected_timeout):
    config = deepcopy(common.CONFIG)

    config['instances'][0].update(timeout_config)

    gitlab_runner = GitlabRunnerCheck('gitlab_runner', common.CONFIG['init_config'], instances=config['instances'])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        gitlab_runner.check(config['instances'][0])

        r.get.assert_called_with(
            'http://localhost:8085/ci',
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=expected_timeout,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )
