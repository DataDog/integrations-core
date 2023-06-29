# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from functools import cached_property
from time import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from httpx import Client

    from ddev.cli.terminal import BorrowedStatus
    from ddev.repo.core import Repository


class PullRequest:
    def __init__(self, data: dict[str, Any]):
        self.__number = str(data['number'])
        self.__title = data['title']
        # Normalize to remove carriage returns on Windows
        self.__body = '\n'.join(data['body'].splitlines())
        self.__author = data['user']['login']
        self.__labels = sorted(label['name'] for label in data['labels'])

    @property
    def number(self) -> str:
        return self.__number

    @property
    def title(self) -> str:
        return self.__title

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
            params={'q': f'sha:{sha}+repo:{self.repo_id}'},
        )
        data = loads(response.text)
        if not data['items']:
            return None

        return PullRequest(data['items'][0])

    def __api_get(self, *args, **kwargs):
        retry_wait = 2
        while True:
            try:
                with self.client as client:
                    response = client.get(*args, auth=self.__auth, **kwargs)

                # https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#rate-limiting
                # https://docs.github.com/en/rest/guides/best-practices-for-integrators?apiVersion=2022-11-28#dealing-with-rate-limits
                if response.status_code == 403 and response.headers['X-RateLimit-Remaining'] == '0':  # noqa: PLR2004
                    self.__status.wait_for(
                        float(response.headers['X-RateLimit-Reset']) - time() + 1,
                        context='GitHub API rate limit reached',
                    )
                    continue
            except Exception as e:
                self.__status.wait_for(retry_wait, context=f'GitHub API error: {e}')
                retry_wait *= 2
                continue

            response.raise_for_status()
            return response
