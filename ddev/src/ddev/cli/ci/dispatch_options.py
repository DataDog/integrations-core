# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Validation for Dispatcher command options."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.cli.ci.dispatch_run import PullRequestResolver

if TYPE_CHECKING:
    from ddev.cli.application import Application


def validate_options(
    app: Application,
    *,
    owner: str,
    repo: str,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_branch: str | None,
    pr_base_branch: str | None,
    commit: str | None,
    all_targets: bool,
    dry_run: bool,
    resolve_only: bool,
    run_manifest: str | None,
) -> tuple[PullRequestResolver | None, str]:
    """Validate run selection and authentication, returning a PR resolver when needed."""
    _validate_modes(app, resolve_only=resolve_only, dry_run=dry_run, run_manifest=run_manifest)
    _validate_manifest_options(
        run_manifest=run_manifest,
        pull_request=pull_request,
        pr_head_sha=pr_head_sha,
        pr_head_repo=pr_head_repo,
        pr_head_branch=pr_head_branch,
        pr_base_branch=pr_base_branch,
        commit=commit,
        all_targets=all_targets,
    )

    resolver = None
    if run_manifest is None:
        resolver = _pull_request_resolver(
            owner=owner,
            repo=repo,
            pull_request=pull_request,
            pr_head_sha=pr_head_sha,
            pr_head_repo=pr_head_repo,
            pr_head_branch=pr_head_branch,
            pr_base_branch=pr_base_branch,
            commit=commit,
        )

    token = _authentication_token(
        app,
        is_pr_run=resolver is not None,
        dry_run=dry_run,
        resolve_only=resolve_only,
    )
    return resolver, token


def _validate_modes(app: Application, *, resolve_only: bool, dry_run: bool, run_manifest: str | None) -> None:
    if resolve_only and run_manifest is not None:
        raise click.UsageError('`--resolve-only` and `--run-manifest` cannot be combined.')
    if resolve_only and dry_run:
        app.display_warning('`--dry-run` has no effect with `--resolve-only`.')


def _validate_manifest_options(
    *,
    run_manifest: str | None,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_branch: str | None,
    pr_base_branch: str | None,
    commit: str | None,
    all_targets: bool,
) -> None:
    if run_manifest is None:
        return

    conflicting = [
        option
        for option, present in {
            '--pr': pull_request is not None,
            '--pr-head-repo': pr_head_repo is not None,
            '--pr-head-branch': pr_head_branch is not None,
            '--pr-head-sha': pr_head_sha is not None,
            '--pr-base-branch': pr_base_branch is not None,
            '--commit': commit is not None,
            '--all': all_targets,
        }.items()
        if present
    ]
    if conflicting:
        raise click.UsageError(
            f'`--run-manifest` supplies the resolved run, so it cannot be combined with `{"`, `".join(conflicting)}`.'
        )


def _pull_request_resolver(
    *,
    owner: str,
    repo: str,
    pull_request: str | None,
    pr_head_sha: str | None,
    pr_head_repo: str | None,
    pr_head_branch: str | None,
    pr_base_branch: str | None,
    commit: str | None,
) -> PullRequestResolver | None:
    from ddev.utils.github import parse_pull_request_reference

    pr_options = {
        '--pr': pull_request,
        '--pr-head-repo': pr_head_repo,
        '--pr-head-branch': pr_head_branch,
        '--pr-head-sha': pr_head_sha,
        '--pr-base-branch': pr_base_branch,
    }
    is_pr_run = any(value is not None for value in pr_options.values())
    if commit is not None and is_pr_run:
        raise click.UsageError('`--commit` cannot be combined with PR options.')
    if not is_pr_run:
        return None

    for option, value in pr_options.items():
        if value == '':
            raise click.UsageError(f'`{option}` must not be empty.')

    number = None
    if pull_request is not None:
        number = parse_pull_request_reference(pull_request)
        if number is None:
            raise click.UsageError(f'`{pull_request}` is neither a pull request number nor a pull request URL.')
    elif not all((pr_head_repo, pr_head_branch, pr_head_sha)):
        raise click.UsageError('Specify `--pr` or all of `--pr-head-repo`, `--pr-head-branch`, and `--pr-head-sha`.')

    if pr_head_repo is not None:
        head_owner, _, head_name = pr_head_repo.partition('/')
        if not head_owner or not head_name or '/' in head_name:
            raise click.UsageError('`--pr-head-repo` must have the form OWNER/NAME.')

    return PullRequestResolver(
        owner=owner,
        repo=repo,
        number=number,
        head_repo=pr_head_repo,
        head_branch=pr_head_branch,
        head_sha=pr_head_sha,
        base_branch=pr_base_branch,
    )


def _authentication_token(app: Application, *, is_pr_run: bool, dry_run: bool, resolve_only: bool) -> str:
    token = app.config.github.token
    if (is_pr_run or (not dry_run and not resolve_only)) and not token:
        app.abort('A GitHub token is required. Set `github.token` in your ddev config.')
    return token
