# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.tooling.commands.agent.common import get_agent_tags


@pytest.mark.parametrize(
    'since, to, expected_result',
    [
        pytest.param('1.0.0', '5.0.0', ['4.5.6', '1.2.3']),
        pytest.param('4.5.6', '5.0.0', ['4.5.6']),
        pytest.param('4.5.6', '8.0.0', ['7.8.9', '4.5.6']),
        pytest.param('1.0.0', None, ['7.8.9', '4.5.6', '1.2.3']),
        pytest.param('8.0.0', None, []),
    ],
)
@mock.patch('datadog_checks.dev.tooling.git.git_tag_list', return_value=['1.2.3', '4.5.6', '7.8.9'])
def test_get_agent_tags(mock_git_tag_list, since, to, expected_result):
    assert get_agent_tags(since=since, to=to) == expected_result
