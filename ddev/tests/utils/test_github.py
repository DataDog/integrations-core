# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from ddev.utils.github import PullRequest


class TestGetPullRequest:
    def test_no_match(self, github_manager, network_replay):
        network_replay('github/get_pr_no_match.yaml')
        assert github_manager.get_pull_request('fcd9c178cb01bcb349c694d34fe6ae237e3c1aa8') is None

    def test_found(self, helpers, network_replay, github_manager):
        network_replay('github/get_pr_found.yaml')

        pr = github_manager.get_pull_request('382cbb0af210897599cbe5fd8d69a38d4017e425')
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


class TestListOpenPullRequestsTargetingBase:
    def test_limit_zero_short_circuit(self, github_manager, mocker):
        api_get = mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_get')
        assert github_manager.list_open_pull_requests_targeting_base('7.99.x', limit=0) == []
        api_get.assert_not_called()

    def test_returns_pull_requests(self, github_manager, mocker):
        response = mocker.MagicMock()
        response.text = (
            '{"items":[{"number":10,"title":"PR title","pull_request":{"html_url":"https://example.invalid/pr/10","diff_url":"https://example.invalid/pr/10.diff"},'
            '"body":"","user":{"login":"someone"},"labels":[{"name":"foo"}]}]}'
        )
        mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_get', return_value=response)

        prs = github_manager.list_open_pull_requests_targeting_base('7.99.x')
        assert len(prs) == 1
        assert prs[0].number == 10
        assert prs[0].title == 'PR title'
        assert prs[0].html_url == 'https://example.invalid/pr/10'
        assert prs[0].labels == ['foo']

    def test_pagination_stops_on_partial_page(self, github_manager, mocker):
        """When a page returns fewer items than requested, pagination stops."""

        def _make_item(n):
            return {
                'number': n,
                'title': f'PR {n}',
                'pull_request': {
                    'html_url': f'https://example.invalid/pr/{n}',
                    'diff_url': f'https://example.invalid/pr/{n}.diff',
                },
                'body': '',
                'user': {'login': 'someone'},
                'labels': [],
            }

        response = mocker.MagicMock()
        response.text = json.dumps({'items': [_make_item(i) for i in range(30)]})
        api_get = mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_get', return_value=response)

        prs = github_manager.list_open_pull_requests_targeting_base('7.99.x', limit=50)
        assert len(prs) == 30
        api_get.assert_called_once()

    def test_result_capped_at_limit(self, github_manager, mocker):
        """Results are truncated to the requested limit."""

        def _make_item(n):
            return {
                'number': n,
                'title': f'PR {n}',
                'pull_request': {
                    'html_url': f'https://example.invalid/pr/{n}',
                    'diff_url': f'https://example.invalid/pr/{n}.diff',
                },
                'body': '',
                'user': {'login': 'someone'},
                'labels': [],
            }

        response = mocker.MagicMock()
        response.text = json.dumps({'items': [_make_item(i) for i in range(10)]})
        api_get = mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_get', return_value=response)

        prs = github_manager.list_open_pull_requests_targeting_base('7.99.x', limit=5)
        assert len(prs) == 5
        api_get.assert_called_once()


class TestCreateLabel:
    def test_create_label(self, network_replay, github_manager):
        network_replay('github/create_label.yaml', record_mode='none')

        github_manager.create_label('my_custom_label', 'ff0000')
        label = github_manager.get_label('my_custom_label')

        assert label.json()['name'] == 'my_custom_label'
        assert label.json()['color'] == 'ff0000'
