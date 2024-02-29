# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from functools import cached_property
from time import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from httpx import Client

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
        from json import loads

        response = self.__api_get(
            self.ISSUE_SEARCH_API,
            # https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
            params={'q': f'sha:{sha} repo:{self.repo_id}'},
        )
        data = loads(response.text)
        if not data['items']:
            return None

        return PullRequest(data['items'][0])

    def get_next_issue_number(self) -> int:
        from json import loads

        number = 1

        response = self.__api_get(
            self.ISSUE_LIST_API.format(repo_id=self.repo_id),
            params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 1},
        )
        data = loads(response.text)
        if data:
            number += data[0]['number']

        return number

    def get_diff(self, pr: PullRequest) -> str:
        response = self.__api_get(pr.diff_url, follow_redirects=True)
        return response.text

    def create_label(self, name, color):
        self.__api_post(
            self.LABELS_API.format(repo_id=self.repo_id), content=json.dumps({'name': name, 'color': color})
        )

    def get_label(self, name):
        return self.__api_get(f'{self.LABELS_API.format(repo_id=self.repo_id)}/{name}')

    def __api_post(self, *args, **kwargs):
        return self.__api_call('post', *args, **kwargs)

    def __api_get(self, *args, **kwargs):
        return self.__api_call('get', *args, **kwargs)

    def __api_call(self, method, *args, **kwargs):
        from httpx import HTTPError

        retry_wait = 2
        while True:
            try:
                response = getattr(self.client, method)(*args, auth=self.__auth, **kwargs)

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
