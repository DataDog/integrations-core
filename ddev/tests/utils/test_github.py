# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import httpx
import pytest
from pytest_mock import MockerFixture

from ddev.utils.github import GitHubManager, PullRequest
from ddev.utils.github_errors import GitHubAuthenticationError


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


@pytest.mark.parametrize('status_code', [401, 403])
def test_authentication_error_has_actionable_token_guidance(
    github_manager: GitHubManager, mocker: MockerFixture, status_code: int
) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core/pulls/1')
    response = httpx.Response(status_code, request=request)
    github_manager.__dict__['client'] = mocker.Mock(get=mocker.Mock(return_value=response))

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        github_manager.get_pr_head(1)

    assert isinstance(exc_info.value, httpx.HTTPStatusError)
    assert isinstance(exc_info.value, httpx.HTTPError)
    assert exc_info.value.response is response
    assert exc_info.value.request is request
    assert f'HTTP {status_code}' in str(exc_info.value)
    assert 'ddev config set github.token' in str(exc_info.value)


def test_primary_rate_limit_is_retried_before_authentication_classification(
    github_manager: GitHubManager, mocker: MockerFixture
) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core/pulls/1')
    rate_limited = httpx.Response(
        403,
        headers={'x-ratelimit-remaining': '0', 'x-ratelimit-reset': '0'},
        request=request,
    )
    success = httpx.Response(200, json={'head': {'sha': 'abc', 'ref': 'feature'}}, request=request)
    client = mocker.Mock(get=mocker.Mock(side_effect=[rate_limited, success]))
    github_manager.__dict__['client'] = client
    wait_for = mocker.patch.object(github_manager._GitHubManager__status, 'wait_for')

    assert github_manager.get_pr_head(1) == ('abc', 'feature')
    assert client.get.call_count == 2
    wait_for.assert_called_once()


@pytest.mark.parametrize(
    ('rate_limit_response', 'expected_wait'),
    [
        (
            httpx.Response(403, headers={'retry-after': '30'}),
            31,
        ),
        (
            httpx.Response(403, json={'message': 'You have exceeded a secondary rate limit.'}),
            61,
        ),
    ],
    ids=['retry_after', 'response_message'],
)
def test_secondary_rate_limit_is_retried_before_authentication_classification(
    github_manager: GitHubManager,
    mocker: MockerFixture,
    rate_limit_response: httpx.Response,
    expected_wait: float,
) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core/pulls/1')
    rate_limit_response.request = request
    success = httpx.Response(200, json={'head': {'sha': 'abc', 'ref': 'feature'}}, request=request)
    client = mocker.Mock(get=mocker.Mock(side_effect=[rate_limit_response, success]))
    github_manager.__dict__['client'] = client
    wait_for = mocker.patch.object(github_manager._GitHubManager__status, 'wait_for')

    assert github_manager.get_pr_head(1) == ('abc', 'feature')
    assert client.get.call_count == 2
    wait_for.assert_called_once_with(expected_wait, context='GitHub API secondary rate limit reached')


def test_secondary_rate_limit_retries_are_bounded(github_manager: GitHubManager, mocker: MockerFixture) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core/pulls/1')
    responses = [
        httpx.Response(403, headers={'retry-after': '30'}, request=request),
        httpx.Response(403, headers={'retry-after': '30'}, request=request),
        httpx.Response(403, headers={'retry-after': '30'}, request=request),
    ]
    client = mocker.Mock(get=mocker.Mock(side_effect=responses))
    github_manager.__dict__['client'] = client
    wait_for = mocker.patch.object(github_manager._GitHubManager__status, 'wait_for')

    with pytest.raises(httpx.HTTPStatusError):
        github_manager.get_pr_head(1)

    assert client.get.call_count == 3
    assert wait_for.call_count == 2


@pytest.mark.parametrize(
    ('method_name', 'args'),
    [
        ('get_changed_files_by_commit_sha', ('abc',)),
        ('get_pull_request_labels', (1,)),
    ],
)
def test_authentication_errors_are_not_swallowed(
    github_manager: GitHubManager,
    mocker: MockerFixture,
    method_name: str,
    args: tuple[object, ...],
) -> None:
    request = httpx.Request('GET', 'https://api.github.com/repos/DataDog/integrations-core')
    response = httpx.Response(403, request=request)
    github_manager.__dict__['client'] = mocker.Mock(get=mocker.Mock(return_value=response))

    with pytest.raises(GitHubAuthenticationError):
        getattr(github_manager, method_name)(*args)
