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

    def test_returns_empty_list_when_no_results(self, github_manager, mocker):
        response = mocker.MagicMock()
        response.text = '{"items":[],"total_count":0}'
        mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_get', return_value=response)

        prs = github_manager.list_open_pull_requests_targeting_base('7.99.x')
        assert prs == []


class TestCreateLabel:
    def test_create_label(self, network_replay, github_manager):
        network_replay('github/create_label.yaml', record_mode='none')

        github_manager.create_label('my_custom_label', 'ff0000')
        label = github_manager.get_label('my_custom_label')

        assert label.json()['name'] == 'my_custom_label'
        assert label.json()['color'] == 'ff0000'


def test_dispatch_workflow_default_returns_none(github_manager, mocker):
    """Default dispatch_workflow keeps the prior fire-and-forget behavior."""
    response = mocker.MagicMock()
    api_post = mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_post', return_value=response)

    result = github_manager.dispatch_workflow(
        workflow_id='example.yaml',
        ref='master',
        inputs={'pr_number': '123', 'head_sha': 'deadbeef'},
    )

    assert result is None
    api_post.assert_called_once()
    payload = json.loads(api_post.call_args.kwargs['content'])
    assert payload == {'ref': 'master', 'inputs': {'pr_number': '123', 'head_sha': 'deadbeef'}}
    assert 'return_run_details' not in payload


def test_dispatch_workflow_return_run_details_sends_flag_and_returns_json(github_manager, mocker):
    """When return_run_details is true, the payload includes the flag and the parsed JSON is returned."""
    run_details = {
        'workflow_run_id': 42,
        'run_url': 'https://api.github.com/repos/o/r/actions/runs/42',
        'html_url': 'https://github.com/o/r/actions/runs/42',
    }
    response = mocker.MagicMock()
    response.json.return_value = run_details
    api_post = mocker.patch('ddev.utils.github.GitHubManager._GitHubManager__api_post', return_value=response)

    result = github_manager.dispatch_workflow(
        workflow_id='example.yaml',
        ref='master',
        inputs={'pr_number': '123', 'head_sha': 'deadbeef'},
        return_run_details=True,
    )

    assert result == run_details
    payload = json.loads(api_post.call_args.kwargs['content'])
    assert payload['return_run_details'] is True
    assert payload['ref'] == 'master'
    assert payload['inputs'] == {'pr_number': '123', 'head_sha': 'deadbeef'}
