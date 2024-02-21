# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository
from ddev.utils.github import GitHubManager, PullRequest


class TestGetPullRequest:
    def test_no_match(self, local_repo, config_file, network_replay, terminal):
        network_replay('github/get_pr_no_match.yaml')

        github = GitHubManager(
            Repository(local_repo.name, str(local_repo)),
            user=config_file.model.github.user,
            token=config_file.model.github.token,
            status=terminal.status,
        )

        assert github.get_pull_request('fcd9c178cb01bcb349c694d34fe6ae237e3c1aa8') is None

    def test_found(self, local_repo, helpers, config_file, network_replay, terminal):
        network_replay('github/get_pr_found.yaml')

        github = GitHubManager(
            Repository(local_repo.name, str(local_repo)),
            user=config_file.model.github.user,
            token=config_file.model.github.token,
            status=terminal.status,
        )

        pr = github.get_pull_request('382cbb0af210897599cbe5fd8d69a38d4017e425')
        assert pr.number == 14849
        assert pr.title == 'Update formatting for changelogs'
        assert pr.body == helpers.dedent(
            """
            ### Motivation

            Make changelogs more readable"""
        )
        assert pr.author == 'swang392'
        assert pr.labels == ['changelog/no-changelog', 'documentation', 'integration/apache']

    @pytest.mark.parametrize(
        'incoming_body, expected_body',
        [
            pytest.param(None, '', id='body is empty'),
            pytest.param(r'abc\r\ndef\n', r'abc\ndef\n', id='body with Windows-style carriage-returns'),
        ],
    )
    def test_pr_description(self, incoming_body, expected_body):
        assert (
            PullRequest(
                {
                    'number': 1,
                    'title': 'Title',
                    'pull_request': {'html_url': 'abc', 'diff_url': 'abc'},
                    'body': incoming_body,
                    'user': {'login': 'mrnobody'},
                    'labels': [],
                }
            ).body
            == expected_body
        )
