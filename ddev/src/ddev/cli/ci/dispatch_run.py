# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Resolve the commit or pull request a Dispatcher invocation tests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.monitoring import ComponentMonitor
    from ddev.utils.git import ChangedFile
    from ddev.utils.github_async import AsyncGitHubClient
    from ddev.utils.github_async.models import PullRequest, PullRequestRef, PullRequestSimple


@dataclass(frozen=True)
class PullRequestResolver:
    """A validated PR number or complete head identity, with optional matching constraints."""

    owner: str
    repo: str
    number: int | None = None
    head_repo: str | None = None
    head_ref: str | None = None
    head_sha: str | None = None
    base_ref: str | None = None

    async def resolve(self, client: AsyncGitHubClient) -> PullRequest | None:
        """Return the matching open PR, or None if it is closed, missing from lookup, or superseded."""
        from ddev.cli.ci.tests.changes import ChangeResolutionError
        from ddev.utils.github_async import PaginationData

        number = self.number
        if number is None:
            assert self.head_repo is not None and self.head_ref is not None and self.head_sha is not None, (
                'PR lookup requires a number or complete head identity.'
            )
            head_owner = self.head_repo.partition('/')[0]
            response = await client.list_pull_requests(
                self.owner, self.repo, state='open', head=f'{head_owner}:{self.head_ref}', base=self.base_ref
            )
            if PaginationData.from_header(response.headers.get('link')).next is not None:
                raise ChangeResolutionError(
                    'Pull request lookup returned more than one page. '
                    'Pass `--pr` with `--pr-head-sha` to identify the pull request.'
                )
            matches = [pull for pull in response.data if self._matches(pull)]
            if not matches:
                return None
            if len(matches) > 1:
                listed = '\n'.join(pull.html_url for pull in sorted(matches, key=lambda pull: pull.number))
                raise ChangeResolutionError(
                    f'Cannot run tests: {len(matches)} open pull requests were found for the commit that '
                    f'triggered this workflow ({self.head_sha}):\n{listed}\n'
                    'A single open pull request is required to run tests.'
                )
            number = matches[0].number

        pull = (await client.get_pull_request(self.owner, self.repo, number)).data
        if pull.head is None or pull.base is None:
            raise ChangeResolutionError(f'Pull request {pull.number} reports no branch references.')
        return pull if self._matches(pull) else None

    def _matches(self, pull: PullRequestSimple) -> bool:
        from ddev.utils.github_async.models import PullRequestState

        if pull.state is not PullRequestState.OPEN or pull.head is None or pull.base is None:
            return False
        if self.head_sha is not None and not pull.head.sha.startswith(self.head_sha):
            return False
        if self.head_repo is not None and (
            pull.head.repo is None or pull.head.repo.full_name.casefold() != self.head_repo.casefold()
        ):
            return False
        if self.head_ref is not None and pull.head.ref != self.head_ref:
            return False
        return self.base_ref is None or pull.base.ref == self.base_ref


@dataclass(frozen=True)
class ResolvedRun:
    """What the run is testing, and the changes it is responsible for.

    ``changed_files`` is None when the plan does not come from a comparison, which is `--all`.
    """

    base_sha: str
    checkout_sha: str
    branch: str
    changed_files: list[ChangedFile] | None
    pr_number: int | None = None
    target_branch: str | None = None
    is_fork: bool = False


def resolve_run(
    app: Application,
    *,
    pr_resolver: PullRequestResolver | None,
    commit: str | None,
    token: str,
    all_targets: bool,
    monitor: ComponentMonitor | None = None,
) -> ResolvedRun | None:
    """Resolve what to test, reporting why a run has nothing left to test before returning None."""
    if pr_resolver is not None:
        return resolve_pull_request_run(
            app, resolver=pr_resolver, token=token, all_targets=all_targets, monitor=monitor
        )

    branch = app.repo.git.current_branch()
    if monitor is not None:
        monitor.logger.info(
            'Resolving tested revision',
            commit=commit,
            branch=branch,
            pr_number=None,
        )
    tested_commit = commit or app.repo.git.latest_commit().sha
    changed_files = None
    if not all_targets:
        from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_commit

        try:
            changed_files = changes_in_commit(app.repo.git, tested_commit)
        except ChangeResolutionError as error:
            if monitor is not None:
                monitor.logger.error('Revision resolution failed', error=str(error))
            app.abort(str(error))

    if monitor is not None:
        monitor.logger.info(
            'Tested revision resolved',
            commit=tested_commit,
            branch=branch,
            changed_file_count=len(changed_files) if changed_files is not None else None,
        )
    return ResolvedRun(
        base_sha=tested_commit,
        checkout_sha=tested_commit,
        branch=branch,
        changed_files=changed_files,
    )


def head_is_fork(head: PullRequestRef, *, owner: str, repo: str) -> bool:
    """Whether a pull request's head branch lives outside the repository being tested.

    A deleted head repository reads as a fork: the value decides whether credentials are withheld, so
    the unknown case is the restrictive one.
    """
    if head.repo is None:
        return True
    return head.repo.full_name.casefold() != f"{owner}/{repo}".casefold()


def resolve_pull_request_run(
    app: Application,
    *,
    resolver: PullRequestResolver,
    token: str,
    all_targets: bool,
    monitor: ComponentMonitor | None = None,
) -> ResolvedRun | None:
    """Read the pull request and its changed files from the API, in one client session."""
    import asyncio

    import httpx
    from pydantic import ValidationError

    from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_pull_request
    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_errors import GitHubAuthenticationError

    if monitor is not None:
        from ddev.monitoring.adapter import ComponentLogAdapter

        client_logger: logging.Logger | None = ComponentLogAdapter(monitor)
        monitor.logger.info('Resolving pull request', pr_number=resolver.number, all_targets=all_targets)
    else:
        client_logger = None

    async def resolve() -> ResolvedRun | None:
        async with async_github_client(token=token, logger=client_logger) as client:
            pull = await resolver.resolve(client)
            if pull is None:
                if monitor is not None:
                    monitor.logger.info('Nothing to test', reason='no open pull request matches the revision')
                app.display_info('No open pull request matches the requested revision, so there is nothing to test.')
                return None
            assert pull.head is not None and pull.base is not None, 'Resolved PRs have branch references.'

            changed_files = None
            if not all_targets:
                if pull.changed_files == 0:
                    if monitor is not None:
                        monitor.logger.info(
                            'Nothing to test', reason='the pull request changes no file', pr_number=pull.number
                        )
                    app.display_info(f'Pull request {pull.number} changes no file, so there is nothing to test.')
                    return None
                changed_files = await changes_in_pull_request(
                    client, resolver.owner, resolver.repo, pull.number, pull.changed_files
                )

            is_fork = head_is_fork(pull.head, owner=resolver.owner, repo=resolver.repo)
            if monitor is not None:
                monitor.logger.info(
                    'Pull request resolved',
                    pr_number=pull.number,
                    branch=pull.head.ref,
                    commit=pull.head.sha,
                    target_branch=pull.base.ref,
                    changed_file_count=pull.changed_files,
                    is_fork=is_fork,
                )
            return ResolvedRun(
                base_sha=pull.head.sha,
                checkout_sha=f'refs/pull/{pull.number}/merge',
                branch=pull.head.ref,
                changed_files=changed_files,
                pr_number=pull.number,
                target_branch=pull.base.ref,
                is_fork=is_fork,
            )

    try:
        return asyncio.run(resolve())
    except GitHubAuthenticationError as error:
        if monitor is not None:
            monitor.logger.error('Pull request resolution failed', error=str(error))
        app.abort(str(error))
    except ChangeResolutionError as error:
        if monitor is not None:
            monitor.logger.error('Pull request resolution failed', error=str(error))
        app.abort(str(error))
    except (httpx.HTTPError, ValidationError) as error:
        if monitor is not None:
            monitor.logger.error('Pull request resolution failed', error=str(error))
        app.abort(f'Could not read the pull request to test: {error}')
