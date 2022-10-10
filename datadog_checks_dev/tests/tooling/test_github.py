# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.dev.tooling.github import get_pr_approvers


@pytest.mark.unit
@pytest.mark.parametrize(
    'github_response, expected_approvers',
    [
        ([], []),
        ([{"user": {"login": "user1"}, "state": "APPROVED"}], ["user1"]),
        ([{"user": {"login": "user1"}, "state": "PENDING"}], []),
        (
            [{"user": {"login": "user1"}, "state": "APPROVED"}, {"user": {"login": "user2"}, "state": "PENDING"}],
            ["user1"],
        ),
    ],
)
def test_get_pr_approvers(github_response, expected_approvers):
    mock_response = mock.MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.json.return_value = github_response

    with mock.patch(
        "requests.get",
        return_value=mock_response,
    ):
        assert get_pr_approvers("integrations-core", "42", {}) == expected_approvers
