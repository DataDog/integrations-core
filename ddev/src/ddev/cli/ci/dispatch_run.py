# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Resolve the commit or pull request a Dispatcher invocation tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ddev.utils.git import ChangedFile

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.cli.application import Application
    from ddev.monitoring import ComponentMonitor
    from ddev.utils.github_async import AsyncGitHubClient
    from ddev.utils.github_async.models import PullRequest, PullRequestRef, PullRequestSimple

RUN_MANIFEST_NAME = 'run.json'


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


class ResolvedRun(BaseModel):
    """What the run is testing, and the changes it is responsible for.

    ``changed_files`` is None when the plan does not come from a comparison, which is `--all`,
    so a null list is also how a manifest says the run covers every target. The model doubles as
    the run manifest's schema: it is written as JSON for a later invocation to load instead of
    resolving again, and `schema_version` gates files this ddev cannot interpret. Bump it
    whenever a field changes meaning.
    """

    model_config = ConfigDict(frozen=True, extra='forbid', populate_by_name=True)

    schema_version: Literal[1] = 1
    repository: str
    base_sha: str = Field(alias='commit_sha')
    checkout_sha: str = Field(alias='checkout_ref')
    branch: str
    changed_files: list[ChangedFile] | None
    pr_number: int | None = None
    target_branch: str | None = None
    target_sha: str | None = None
    is_fork: bool = False


def write_run_manifest(base_path: Path, *, run: ResolvedRun) -> None:
    """Write the resolved run's manifest as machine-readable JSON under its output directory.

    Written before planning, so the manifest exists for `--resolve-only` runs, dry runs, and runs
    whose plan turns out empty. A stale or missing pull request resolves no run and so produces
    no manifest.
    """
    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / RUN_MANIFEST_NAME).write_text(f'{run.model_dump_json(by_alias=True, indent=2)}\n', encoding='utf-8')


def load_run_manifest(app: Application, path: Path, *, repository: str) -> ResolvedRun:
    """Read a run resolved by an earlier invocation, refusing a manifest that cannot be trusted.

    The manifest is the run: nothing is looked up again, so a file that does not describe a usable
    run stops the invocation here rather than planning from something unreadable. The repository
    check sits outside the model because only this caller knows which repository was asked for.
    """
    try:
        run = ResolvedRun.model_validate_json(path.read_text(encoding='utf-8'))
    except OSError as error:
        app.abort(f'Could not read run manifest {path}: {error}')
    except ValidationError as error:
        app.abort(f'Run manifest {path} is not a valid run: {error}')

    if run.repository.casefold() != repository.casefold():
        app.abort(f'Run manifest {path} describes repository {run.repository}, not {repository}.')

    return run


def resolve_run(
    app: Application,
    *,
    repository: str,
    pr_resolver: PullRequestResolver | None,
    commit: str | None,
    token: str,
    all_targets: bool,
    monitor: ComponentMonitor | None = None,
) -> ResolvedRun | None:
    """Resolve what to test, reporting why a run has nothing left to test before returning None."""
    if pr_resolver is not None:
        return resolve_pull_request_run(
            app, repository=repository, resolver=pr_resolver, token=token, all_targets=all_targets
        )

    tested_commit = commit or app.repo.git.latest_commit().sha
    changed_files = None
    if not all_targets:
        from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_commit

        try:
            changed_files = changes_in_commit(app.repo.git, tested_commit)
        except ChangeResolutionError as error:
            app.abort(str(error))

    return ResolvedRun(
        repository=repository,
        base_sha=tested_commit,
        checkout_sha=tested_commit,
        branch=app.repo.git.current_branch(),
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
    repository: str,
    resolver: PullRequestResolver,
    token: str,
    all_targets: bool,
) -> ResolvedRun | None:
    """Read the pull request and its changed files from the API, in one client session."""
    import asyncio

    import httpx

    from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_pull_request
    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_errors import GitHubAuthenticationError

    async def resolve() -> ResolvedRun | None:
        async with async_github_client(token=token) as client:
            pull = await resolver.resolve(client)
            if pull is None:
                app.display_info('No open pull request matches the requested revision, so there is nothing to test.')
                return None
            assert pull.head is not None and pull.base is not None, 'Resolved PRs have branch references.'

            changed_files = None
            if not all_targets:
                if pull.changed_files == 0:
                    app.display_info(f'Pull request {pull.number} changes no file, so there is nothing to test.')
                    return None
                changed_files = await changes_in_pull_request(
                    client, resolver.owner, resolver.repo, pull.number, pull.changed_files
                )

            return ResolvedRun(
                repository=repository,
                base_sha=pull.head.sha,
                checkout_sha=f'refs/pull/{pull.number}/merge',
                branch=pull.head.ref,
                changed_files=changed_files,
                pr_number=pull.number,
                target_branch=pull.base.ref,
                target_sha=pull.base.sha,
                is_fork=head_is_fork(pull.head, owner=resolver.owner, repo=resolver.repo),
            )

    try:
        return asyncio.run(resolve())
    except GitHubAuthenticationError as error:
        app.abort(str(error))
    except ChangeResolutionError as error:
        app.abort(str(error))
    except (httpx.HTTPError, ValidationError) as error:
        app.abort(f'Could not read the pull request to test: {error}')
