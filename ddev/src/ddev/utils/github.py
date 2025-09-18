# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from functools import cached_property
from time import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

    from httpx import Client, Response

    from ddev.cli.terminal import BorrowedStatus
    from ddev.repo.core import Repository


class PullRequest:
    def __init__(self, data: dict[str, Any]):
        self.__number = data['number']
        self.__title = data['title']
        self.__html_url = data['pull_request']['html_url']
        self.__diff_url = data['pull_request']['diff_url']
        # Github API returns `None` for empty bodies, but we use empty string as default.
        # Normalize to remove carriage returns on Windows.
        raw_body = data['body']
        self.__body = ('' if raw_body is None else raw_body).replace(r'\r', '')
        self.__author = data['user']['login']
        self.__labels = sorted(label['name'] for label in data['labels'])

    @property
    def number(self) -> int:
        return self.__number

    @property
    def title(self) -> str:
        return self.__title

    @property
    def html_url(self) -> str:
        return self.__html_url

    @property
    def diff_url(self) -> str:
        return self.__diff_url

    @property
    def body(self) -> str:
        return self.__body

    @property
    def author(self) -> str:
        return self.__author

    @property
    def labels(self) -> list[str]:
        return self.__labels


class GitHubManager:
    API_VERSION = '2022-11-28'

    # https://docs.github.com/en/rest/search?apiVersion=2022-11-28#search-issues-and-pull-requests
    ISSUE_SEARCH_API = 'https://api.github.com/search/issues'

    # https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues
    ISSUE_LIST_API = 'https://api.github.com/repos/{repo_id}/issues'

    # https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28#create-a-label
    LABELS_API = 'https://api.github.com/repos/{repo_id}/labels'

    # https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files
    PULL_REQUEST_FILES_API = 'https://api.github.com/repos/{repo_id}/pulls/{pr_number}/files'

    # https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#list-commits-on-a-repository
    COMMIT_API = 'https://api.github.com/repos/{repo_id}/commits/{sha}'

    # https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2022-11-28#list-workflow-runs-for-a-repository
    ACTION_RUNS_API = 'https://api.github.com/repos/{repo_id}/actions/runs'

    # https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#list-repository-workflows
    WORKFLOWS_API = 'https://api.github.com/repos/{repo_id}/actions/workflows'

    def __init__(self, repo: Repository, *, user: str, token: str, status: BorrowedStatus):
        self.__repo = repo
        self.__auth = (user, token)
        self.__status = status
        self.__repo_id = f'DataDog/{self.__repo.full_name}'

    @property
    def repo_id(self) -> str:
        return self.__repo_id

    @cached_property
    def client(self) -> Client:
        from httpx import Client

        # https://docs.github.com/en/rest/overview/api-versions?apiVersion=2022-11-28#specifying-an-api-version
        client = Client(headers={'X-GitHub-Api-Version': self.API_VERSION})

        return client

    def get_pull_request(self, sha: str) -> PullRequest | None:
        response = self.__api_get(
            self.ISSUE_SEARCH_API,
            # https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
            params={'q': f'sha:{sha} repo:{self.repo_id} is:pull-request'},
        )
        data = json.loads(response.text)
        if not data['items']:
            return None

        return PullRequest(data['items'][0])

    def get_pull_request_by_number(self, number: str) -> PullRequest | None:
        response = self.__api_get(
            self.ISSUE_SEARCH_API,
            params={'q': f'{number} repo:{self.repo_id} is:pull-request'},
        )
        data = json.loads(response.text)
        if not data['items']:
            return None

        return PullRequest(data['items'][0])

    def get_next_issue_number(self) -> int:
        number = 1

        response = self.__api_get(
            self.ISSUE_LIST_API.format(repo_id=self.repo_id),
            params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 1},
        )
        data = json.loads(response.text)
        if data:
            number += data[0]['number']

        return number

    def get_diff(self, pr: PullRequest) -> str:
        response = self.__api_get(pr.diff_url, follow_redirects=True)
        return response.text

    def get_changed_files_by_pr(self, pr: PullRequest) -> list[str]:
        response = self.__api_get(self.PULL_REQUEST_FILES_API.format(repo_id=self.repo_id, pr_number=pr.number))
        return [file_data['filename'] for file_data in response.json()]

    def get_changed_files_by_commit_sha(self, sha: str) -> list[str] | None:
        from httpx import HTTPStatusError

        try:
            response = self.__api_get(self.COMMIT_API.format(repo_id=self.repo_id, sha=sha))
        except HTTPStatusError:
            return None
        return [file_data['filename'] for file_data in response.json().get('files', [])]

    def create_label(self, name, color):
        self.__api_post(
            self.LABELS_API.format(repo_id=self.repo_id), content=json.dumps({'name': name, 'color': color})
        )

    def get_label(self, name):
        return self.__api_get(f'{self.LABELS_API.format(repo_id=self.repo_id)}/{name}')

    def get_workflows(self) -> Generator[dict[str, Any]]:
        yield from self.__paginate(
            "get",
            url=self.WORKFLOWS_API.format(repo_id=self.repo_id),
            element_key='workflows',
        )

    def get_workflow(self, workflow_name: str) -> dict[str, Any] | None:
        if not workflow_name.startswith('.github/workflows/'):
            workflow_name = f'.github/workflows/{workflow_name}'

        for workflow in self.get_workflows():
            if workflow['path'] == workflow_name:
                return workflow
        return None

    def get_repo_workflow_runs(
        self,
        *,
        commit_sha: str | None = None,
        branch: str | None = None,
        event: str | None = None,
        status: str | None = None,
        per_page: int = 30,
    ) -> Generator[Any]:
        """
        Get the list of workflows run for a specific commit.

        Parameters:
            commit_sha: The SHA of the commit to get the workflows for.
            branch: The branch to get the workflows for.
            event: The event to get the workflows for.
            status: The status to get the workflows for.
            per_page: The number of workflows to get per page.

        Returns:
            A generator of workflows run for the upplied parameters.
        """
        params = {
            'head_sha': commit_sha,
            'branch': branch,
            'event': event,
            'status': status,
            'per_page': per_page,
        }

        yield from self.__paginate(
            "get",
            url=self.ACTION_RUNS_API.format(repo_id=self.repo_id),
            element_key='workflow_runs',
            params={k: v for k, v in params.items() if v is not None},
        )

    def get_workflow_runs_by_workflow_name(
        self,
        *,
        workflow_name: str,
        commit_sha: str | None = None,
        branch: str | None = None,
        event: str | None = None,
        status: str | None = None,
        per_page: int = 30,
    ) -> Generator[Any]:
        workflow = self.get_workflow(workflow_name)

        if workflow is None:
            raise ValueError(f'Workflow {workflow_name} not found')

        params = {
            'head_sha': commit_sha,
            'branch': branch,
            'event': event,
            'status': status,
            'per_page': per_page,
        }

        yield from self.__paginate(
            "get",
            url=f"{self.WORKFLOWS_API.format(repo_id=self.repo_id)}/{workflow['id']}/runs",
            element_key='workflow_runs',
            params={k: v for k, v in params.items() if v is not None},
        )

    def __paginate(self, method: str, *, url: str, element_key: str, **kwargs) -> Generator[dict[str, Any]]:
        """
        Pagine over the results of the API call.

        The pagination will be done over the elment of the json response represented by the element_key.
        """
        next_page = url
        while next_page:
            response = self.__api_call(method, next_page, **kwargs)
            elements = response.json().get(element_key)

            if not isinstance(elements, list):
                raise ValueError(f'The element key {element_key} is not iterable')

            yield from elements

            next_page = response.links.get('next', {}).get('url')
            # Params will be included int he next page, pop it if supplied
            kwargs.pop('params', None)

    def __api_post(self, url: str, **kwargs):
        return self.__api_call('post', url, **kwargs)

    def __api_get(self, url: str, **kwargs):
        return self.__api_call('get', url, **kwargs)

    def __api_call(self, method: str, url: str, **kwargs) -> Response:
        from httpx import HTTPError

        retry_wait = 2
        while True:
            try:
                response = self.client.request(method, url, auth=self.__auth, **kwargs)

                # https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#rate-limiting
                # https://docs.github.com/en/rest/guides/best-practices-for-integrators?apiVersion=2022-11-28#dealing-with-rate-limits
                if response.status_code == 403 and response.headers['X-RateLimit-Remaining'] == '0':  # noqa: PLR2004
                    self.__status.wait_for(
                        float(response.headers['X-RateLimit-Reset']) - time() + 1,
                        context='GitHub API rate limit reached',
                    )
                    continue
            except HTTPError as e:
                self.__status.wait_for(retry_wait, context=f'GitHub API error: {e}')
                retry_wait *= 2
                continue

            response.raise_for_status()
            return response
