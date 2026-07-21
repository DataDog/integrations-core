# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Workflow internals for the `ddev release port-commit` command.

Kept in a separate module so the command file stays small and the workflow
classes are not imported on `--help` or other command-listing operations.
Import this module from inside the command body, not at module top level.

The workflow runs in an isolated git worktree at `.worktrees/port-commit/<branch>/`
so the user's primary working tree is never mutated. On success the worktree is
removed; on failure it is left in place for the user to inspect or finish manually.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

import click
from rich.panel import Panel
from rich.text import Text

from ddev.utils.fs import Path
from ddev.utils.git import GitRepository

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.utils.github_async.models import PullRequest


PR_NUMBER_SUFFIX_PATTERN = re.compile(r'\s*\(#(\d+)\)\s*$')
PR_TEMPLATE_RELATIVE_PATH = '.github/PULL_REQUEST_TEMPLATE.md'
PR_TEMPLATE_HEADING = '### What does this PR do?'
WORKTREE_BASE = '.worktrees/port-commit'
FULL_SHA_PATTERN = re.compile(r'^[0-9a-fA-F]{40}$')
HEX_PATTERN = re.compile(r'^[0-9a-fA-F]+$')
DIGITS_PATTERN = re.compile(r'^\d+$')
PR_PREFIX_PATTERN = re.compile(r'^PR-(\d+)$', re.IGNORECASE)
PR_URL_PATTERN = re.compile(r'^https?://github\.com/[^/]+/[^/]+/pull/(\d+)(?:[/?#].*)?$', re.IGNORECASE)

# Paths whose content is regenerated per-branch, so a backport must reset them to the target
# branch's version instead of carrying over the source commit's. A trailing slash matches as a
# path prefix anchored at the repo root; an entry without one matches as a substring anywhere.
RESETTABLE_PATHS = (
    # `.in-toto` supply-chain attestations (e.g. `*.in-toto.link`) are per-branch and cannot be
    # cherry-picked; they live in subdirectories, so match the substring anywhere in the path.
    '.in-toto',
    # `.deps/` lockfiles are regenerated per release branch; a cherry-picked dependency bump would
    # otherwise drag in the source branch's lockfile. Anchored at the repo root.
    '.deps/',
)
RESETTABLE_PATHS_DISPLAY = ', '.join(f'`{path}`' for path in RESETTABLE_PATHS)

# Prefix of the labels that request a backport, e.g. `backport/7.62.x` targets the `7.62.x` branch.
BACKPORT_LABEL_PREFIX = 'backport/'


class PortStepError(Exception):
    """Raised by a PortStep to signal a clean abort with a user-facing message."""


class _CommitNotResolvable(Exception):
    """Raised when a commit input cannot be resolved locally or via a SHA-targeted fetch."""


class _PRNotFound(Exception):
    """Raised when a PR lookup returns 404 so the caller can fall back to commit resolution."""


class PortStep:
    """Single step of the port-commit workflow."""

    def __init__(self, app: Application, *, dry_run: bool = False) -> None:
        self.app = app
        self.dry_run = dry_run

    def describe(self) -> str:
        raise NotImplementedError

    def planned_commands(self) -> list[str]:
        return []

    def execute(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
        if self.dry_run:
            self.app.display_info(self.describe())
            for cmd in self.planned_commands():
                self.app.display_info(f'  (dry-run) {cmd}')
            return

        self.app.output(Text(f'{self.describe()}...'), stderr=True)
        try:
            self.execute()
        except PortStepError:
            raise
        except OSError as e:
            raise PortStepError(str(e)) from e

        self.app.output(Text(f'{self.describe()}: done.', style='cyan'), stderr=True)
        self.app.output('', stderr=True)


class FetchOriginStep(PortStep):
    def __init__(self, app: Application, *, git: GitRepository, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.git = git

    def describe(self) -> str:
        return 'Fetching latest changes from origin'

    def planned_commands(self) -> list[str]:
        return ['git fetch origin']

    def execute(self) -> None:
        self.git.run('fetch', 'origin')


class SetupWorktreeStep(PortStep):
    """Create the isolated worktree on a fresh port branch."""

    def __init__(
        self,
        app: Application,
        *,
        main_git: GitRepository,
        worktree_path: Path,
        branch: str,
        target: str,
        dry_run: bool = False,
    ) -> None:
        super().__init__(app, dry_run=dry_run)
        self.main_git = main_git
        self.worktree_path = worktree_path
        self.branch = branch
        self.target = target

    def describe(self) -> str:
        return (
            f'Creating worktree at `{self.worktree_path}` on new branch `{self.branch}` '
            '(resetting if branch already exists)'
        )

    def planned_commands(self) -> list[str]:
        return [
            f'git worktree add -B {self.branch} {self.worktree_path} origin/{self.target} '
            '# -B resets the branch if it already exists locally',
        ]

    def execute(self) -> None:
        self.worktree_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.main_git.run('worktree', 'add', '-B', self.branch, str(self.worktree_path), f'origin/{self.target}')
        except OSError as e:
            raise PortStepError(f'Failed to create worktree at `{self.worktree_path}`: {e}') from e


class TeardownWorktreeStep(PortStep):
    """Remove the worktree on a successful run."""

    def __init__(
        self,
        app: Application,
        *,
        main_git: GitRepository,
        worktree_path: Path,
        dry_run: bool = False,
    ) -> None:
        super().__init__(app, dry_run=dry_run)
        self.main_git = main_git
        self.worktree_path = worktree_path

    def describe(self) -> str:
        return f'Removing worktree at `{self.worktree_path}`'

    def planned_commands(self) -> list[str]:
        return [f'git worktree remove --force {self.worktree_path}']

    def execute(self) -> None:
        self.main_git.run('worktree', 'remove', '--force', str(self.worktree_path))


class CherryPickStep(PortStep):
    """Cherry-pick a commit, auto-resolving conflicts in regenerated files (see `RESETTABLE_PATHS`)."""

    def __init__(self, app: Application, *, git: GitRepository, sha: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.git = git
        self.sha = sha

    def describe(self) -> str:
        return f'Cherry-picking {self.sha[:10]}'

    def planned_commands(self) -> list[str]:
        return [f'git cherry-pick --no-commit {self.sha}']

    def execute(self) -> None:
        try:
            self.git.run('cherry-pick', '--no-commit', self.sha)
            return
        except OSError:
            pass

        conflicts = [line for line in self.git.capture('diff', '--name-only', '--diff-filter=U').splitlines() if line]
        resettable = [f for f in conflicts if is_reset_to_target(f)]
        manual = [f for f in conflicts if not is_reset_to_target(f)]

        if manual:
            try:
                self.git.run('cherry-pick', '--abort')
            except OSError:
                pass
            listing = '\n  '.join(manual)
            raise PortStepError(
                f'Cherry-pick has conflicts outside regenerated files ({RESETTABLE_PATHS_DISPLAY}):\n  {listing}'
            )

        if not resettable:
            raise PortStepError('Cherry-pick failed without conflicts. Resolve manually and try again.')

        for path in resettable:
            _resolve_reset_to_target_conflict(self.git, path)


class PreserveGeneratedFilesStep(PortStep):
    """Reset staged changes in regenerated files (see `RESETTABLE_PATHS`) back to the target branch's versions."""

    def __init__(self, app: Application, *, git: GitRepository, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.git = git

    def describe(self) -> str:
        return f'Preserving generated files ({RESETTABLE_PATHS_DISPLAY}) from target branch'

    def planned_commands(self) -> list[str]:
        return [f'# Reset any staged {RESETTABLE_PATHS_DISPLAY} changes to HEAD']

    def execute(self) -> None:
        staged = [line for line in self.git.capture('diff', '--cached', '--name-only').splitlines() if line]
        affected = [f for f in staged if is_reset_to_target(f)]
        if not affected:
            return

        for path in affected:
            _restore_path_from_head(self.git, path)


class CommitStep(PortStep):
    def __init__(
        self,
        app: Application,
        *,
        git: GitRepository,
        subject: str,
        verify: bool = False,
        dry_run: bool = False,
    ) -> None:
        super().__init__(app, dry_run=dry_run)
        self.git = git
        self.subject = subject
        self.verify = verify

    @property
    def message(self) -> str:
        return f'[Backport] {self.subject}'

    def describe(self) -> str:
        return f'Committing changes as "{self.message}"'

    def planned_commands(self) -> list[str]:
        flags = '' if self.verify else '--no-verify '
        return [f'git commit {flags}-m "{self.message}"']

    def execute(self) -> None:
        args = ['commit', '-m', self.message]
        if not self.verify:
            args.insert(1, '--no-verify')
        self.git.run(*args)


class PushStep(PortStep):
    def __init__(self, app: Application, *, git: GitRepository, branch: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.git = git
        self.branch = branch

    def describe(self) -> str:
        return f'Pushing `{self.branch}` to origin'

    def planned_commands(self) -> list[str]:
        return [f'git push origin {self.branch}']

    def execute(self) -> None:
        self.git.run('push', 'origin', self.branch)


class CreatePullRequestStep(PortStep):
    def __init__(
        self,
        app: Application,
        *,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str,
        labels: list[str],
        draft: bool,
        dry_run: bool = False,
    ) -> None:
        super().__init__(app, dry_run=dry_run)
        self.owner = owner
        self.repo = repo
        self.title = title
        self.head = head
        self.base = base
        self.body = body
        self.labels = labels
        self.draft = draft
        self.pr_url: str | None = None

    def describe(self) -> str:
        flavor = 'draft pull request' if self.draft else 'pull request'
        return f'Creating {flavor} `{self.title}`'

    def planned_commands(self) -> list[str]:
        label_part = f' --label {",".join(self.labels)}' if self.labels else ''
        draft_part = ' --draft' if self.draft else ''
        endpoint = f'/repos/{self.owner}/{self.repo}/pulls'
        return [f'POST {endpoint} (head={self.head}, base={self.base}{draft_part}){label_part}']

    def execute(self) -> None:
        import asyncio

        import httpx
        from pydantic import ValidationError

        try:
            asyncio.run(self._create_pr())
        except (httpx.HTTPError, ValidationError) as e:
            if self.pr_url:
                raise PortStepError(
                    f'Pull request created at {self.pr_url} but labeling failed: {e}. '
                    'Add the labels manually on the PR.'
                ) from e
            raise PortStepError(f'Failed to create pull request: {e}') from e

    async def _create_pr(self) -> None:
        from ddev.utils.github_async import async_github_client

        async with async_github_client(token=self.app.config.github.token) as client:
            response = await client.create_pull_request(
                owner=self.owner,
                repo=self.repo,
                title=self.title,
                head=self.head,
                base=self.base,
                body=self.body,
                draft=self.draft,
            )
            pr = response.data
            self.pr_url = pr.html_url
            if self.labels:
                await client.add_labels_to_issue(
                    owner=self.owner,
                    repo=self.repo,
                    issue_number=pr.number,
                    labels=self.labels,
                )


def _resolve_input(app: Application, raw: str, *, dry_run: bool) -> str:
    """Resolve the raw user input to a full commit SHA.

    Handles three input shapes:
    - Explicit PR form (`PR-12345` or a GitHub PR URL) -> looks up the PR.
    - All-digits (e.g. `12345`) with a GitHub token configured -> tries as a PR; on 404 falls
      back to commit resolution. Without a token the PR step is skipped.
    - Anything else -> commit resolution.

    Raises `_CommitNotResolvable` when nothing matches so the caller can decide how to abort.
    """
    raw = raw.strip()
    pr_number = _extract_explicit_pr_number(raw)
    if pr_number is not None:
        return _resolve_pr_to_commit(app, pr_number, dry_run=dry_run)

    is_digits = DIGITS_PATTERN.fullmatch(raw) is not None
    if is_digits and app.config.github.token:
        with contextlib.suppress(_PRNotFound):
            return _resolve_pr_to_commit(app, int(raw), dry_run=dry_run)

    try:
        return _resolve_commit_or_fetch(app, raw, dry_run=dry_run)
    except _CommitNotResolvable as exc:
        if is_digits:
            raise _CommitNotResolvable(
                f'Could not resolve `{raw}` as a PR or a commit. '
                'Pass the full 40-character SHA, or `PR-xxxxx` / a PR URL to disambiguate.'
            ) from exc
        raise


def _extract_explicit_pr_number(raw: str) -> int | None:
    """Return the PR number when `raw` is a `PR-12345` token or a GitHub PR URL, else None."""
    for pattern in (PR_PREFIX_PATTERN, PR_URL_PATTERN):
        match = pattern.fullmatch(raw)
        if match:
            return int(match.group(1))
    return None


def _resolve_pr(
    app: Application, pr_number: int, *, dry_run: bool, missing_token_message: str | None = None
) -> tuple[PullRequest, str]:
    """Fetch PR #<pr_number> and resolve its squash-merge commit to a full SHA.

    Returns `(pull_request, full_sha)`. Raises `_PRNotFound` when GitHub returns 404. Raises
    `_CommitNotResolvable` (wrapped with PR context) when the merge commit can't be resolved locally.
    Aborts on other auth / network / validation errors, or when the PR is not squash-merged, so the
    user gets a clear, contextual message rather than a stack trace. `missing_token_message` lets a
    caller replace the default no-token abort text with one tailored to its entry point.
    """
    import asyncio

    import httpx
    from pydantic import ValidationError

    if not app.config.github.token:
        app.abort(
            missing_token_message
            or (
                'GitHub token required to resolve a PR reference. Set `github.token`, or pass the '
                'full commit SHA directly (--no-pr does not skip this lookup).'
            )
        )

    owner, repo = resolve_owner_repo(app)
    app.display_info(f'Resolving PR #{pr_number} via GitHub...')
    try:
        pr = asyncio.run(_fetch_pr(app.config.github.token, owner, repo, pr_number))
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            raise _PRNotFound(str(pr_number)) from exc
        if status in (401, 403):
            app.abort(
                f'GitHub denied the request for PR #{pr_number} (HTTP {status}). '
                'Check that `github.token` is set and has `repo` scope.'
            )
        app.abort(f'Failed to fetch PR #{pr_number} from GitHub: {exc}.')
    except (httpx.HTTPError, ValidationError) as exc:
        app.abort(f'Failed to fetch PR #{pr_number} from GitHub: {exc}.')

    if not pr.merged:
        app.abort(f'PR #{pr_number} is not merged; nothing to backport.')

    if not pr.merge_commit_sha:
        app.abort(f'PR #{pr_number} has no merge commit SHA available.')

    try:
        full_sha = _resolve_commit_or_fetch(app, pr.merge_commit_sha, dry_run=dry_run)
    except _CommitNotResolvable as exc:
        raise _CommitNotResolvable(
            f'PR #{pr_number} was found but its merge commit `{pr.merge_commit_sha}` could not be resolved: {exc}'
        ) from exc
    _abort_if_merge_commit(app, pr_number, full_sha)
    return pr, full_sha


def _resolve_pr_to_commit(app: Application, pr_number: int, *, dry_run: bool) -> str:
    """Resolve a PR number to the full SHA of its squash-merge commit (see `_resolve_pr`)."""
    _, full_sha = _resolve_pr(app, pr_number, dry_run=dry_run)
    return full_sha


async def _fetch_pr(token: str, owner: str, repo: str, pr_number: int) -> PullRequest:
    from ddev.utils.github_async import async_github_client

    async with async_github_client(token=token) as client:
        response = await client.get_pull_request(owner=owner, repo=repo, pull_number=pr_number)
        return response.data


def _abort_if_merge_commit(app: Application, pr_number: int, full_sha: str) -> None:
    """Abort when `full_sha` is a merge commit (>= 2 parents), which can't be backported as a single commit."""
    try:
        raw = app.repo.git.capture('rev-list', '--parents', '-n1', full_sha)
    except OSError as exc:
        app.abort(f'Could not inspect merge parents of `{full_sha}`: {exc}.')
    else:
        parent_count = max(len(raw.strip().split()) - 1, 0)
        if parent_count >= 2:
            app.abort(
                f"PR #{pr_number} was not squash-merged, so there isn't a single commit to backport "
                'the full PR. Run again with the specific commit you want to backport.'
            )


def _resolve_commit_or_fetch(app: Application, commit_hash: str, *, dry_run: bool) -> str:
    """Return the full SHA for `commit_hash`, fetching from origin when the commit is not local.

    Raises `_CommitNotResolvable` when the commit is neither available locally nor reachable on
    origin. Falling back to a SHA-targeted fetch lets the command port commits that live on remote
    branches the local repo does not track (the `remote.origin.fetch` refspec is often narrowed in
    this repo to avoid pulling thousands of branches).

    When `dry_run` is true, the fetch fallback is skipped to preserve the dry-run contract: a
    non-local commit raises instead of mutating local state.
    """
    git = app.repo.git
    with contextlib.suppress(OSError):
        return git.capture('rev-parse', '--verify', f'{commit_hash}^{{commit}}').strip()

    # Abbreviated SHAs cannot be fetched (GitHub's allowReachableSHA1InWant only honours full
    # SHAs), so this is the real diagnosis regardless of dry-run mode. Surface it first.
    if HEX_PATTERN.fullmatch(commit_hash) and not FULL_SHA_PATTERN.fullmatch(commit_hash):
        raise _CommitNotResolvable(
            f'Commit `{commit_hash}` is not in the local repository. '
            'Pass the full 40-character SHA so it can be fetched from origin '
            '(GitHub does not support SHA-targeted fetches for abbreviated SHAs).'
        )

    if dry_run:
        raise _CommitNotResolvable(
            f'Commit `{commit_hash}` is not in the local repository. '
            'Re-run without `--dry-run` to fetch it from origin, or pre-fetch the commit manually.'
        )

    app.display_info(f'Commit `{commit_hash}` not found locally; fetching from origin.')
    fetched = False
    with contextlib.suppress(OSError):
        git.run('fetch', 'origin', commit_hash)
        fetched = True

    if fetched:
        with contextlib.suppress(OSError):
            return git.capture('rev-parse', '--verify', f'{commit_hash}^{{commit}}').strip()

    raise _CommitNotResolvable(f'Commit `{commit_hash}` does not exist locally or on origin.')


def is_reset_to_target(path: str) -> bool:
    """Whether a path holds per-branch regenerated content that must be reset to the target branch."""
    return any(path.startswith(entry) if entry.endswith('/') else entry in path for entry in RESETTABLE_PATHS)


def _path_exists_in_head(git: GitRepository, path: str) -> bool:
    try:
        git.capture('cat-file', '-e', f'HEAD:{path}')
        return True
    except OSError:
        return False


def _resolve_reset_to_target_conflict(git: GitRepository, path: str) -> None:
    if not _path_exists_in_head(git, path):
        git.run('rm', '--force', path)
        return
    git.run('checkout', '--ours', path)
    # `.in-toto/` is gitignored, so `git add` refuses without `--force` even though the path is
    # tracked in HEAD; for tracked `.deps/` files the force is a harmless no-op. Safe either way:
    # we only reach here for paths from `git diff --diff-filter=U`, i.e. files git itself flagged.
    git.run('add', '--force', path)


def _restore_path_from_head(git: GitRepository, path: str) -> None:
    if not _path_exists_in_head(git, path):
        git.run('rm', '--force', path)
        return
    git.run('checkout', 'HEAD', '--', path)


def split_commit_subject(subject: str) -> tuple[str, str | None]:
    """Return (subject_without_pr_suffix, original_pr_number_or_None)."""
    match = PR_NUMBER_SUFFIX_PATTERN.search(subject)
    if not match:
        return subject, None
    return PR_NUMBER_SUFFIX_PATTERN.sub('', subject), match.group(1)


def build_pr_body(
    app: Application, *, sha: str, subject: str, target: str, original_pr: str | None, owner: str, repo: str
) -> str:
    commit_link = f'[`{sha[:10]}`](https://github.com/{owner}/{repo}/commit/{sha})'
    info_lines = [f'**Backported commit**: {commit_link} - {subject}']
    if original_pr:
        info_lines.append(f'**Original PR**: #{original_pr}')
    info_lines.append(f'**Target branch**: `{target}`')
    info_block = '\n'.join(info_lines) + '\n'

    template_path = app.repo.path / PR_TEMPLATE_RELATIVE_PATH
    if not template_path.is_file():
        return f'{PR_TEMPLATE_HEADING}\n\n{info_block}'

    template = template_path.read_text()
    if PR_TEMPLATE_HEADING in template:
        return template.replace(PR_TEMPLATE_HEADING, f'{PR_TEMPLATE_HEADING}\n\n{info_block}', 1)
    return f'{info_block}\n{template}'


def parse_labels(raw: str) -> list[str]:
    return [label.strip() for label in raw.split(',') if label.strip()]


def derive_backport_bases(pr: PullRequest) -> list[str]:
    """Return the target branches from a PR's `backport/<base>` labels, in order and de-duplicated."""
    bases: list[str] = []
    for label in pr.labels:
        if label.name.startswith(BACKPORT_LABEL_PREFIX):
            base = label.name[len(BACKPORT_LABEL_PREFIX) :]
            if base and base not in bases:
                bases.append(base)
    return bases


def resolve_owner_repo(app: Application) -> tuple[str, str]:
    """Resolve (owner, repo) for the active repository.

    Falls back to `DataDog/<full_name>` when `full_name` is unqualified.
    """
    full = app.repo.full_name
    if '/' in full:
        owner, repo = full.split('/', 1)
        return owner, repo
    return 'DataDog', full


def _sanitize_branch_for_path(branch: str) -> str:
    return branch.replace('/', '-')


def _worktree_path_for(app: Application, branch: str) -> Path:
    return app.repo.path / WORKTREE_BASE / _sanitize_branch_for_path(branch)


@dataclass(frozen=True)
class PortPlan:
    """All values needed to execute the port workflow, resolved up front."""

    full_sha: str
    clean_subject: str
    original_pr: str | None
    target_branch: str
    new_branch: str
    worktree_path: Path
    pr_title: str
    pr_body: str
    labels: list[str]
    draft: bool
    create_pr: bool
    verify: bool
    dry_run: bool


@dataclass(frozen=True)
class PortOptions:
    """Raw user-supplied knobs shared by every port, independent of the specific commit or base."""

    branch_prefix: str
    branch_suffix: str | None
    pr_labels: str
    no_pr: bool
    draft: bool
    verify: bool
    dry_run: bool


def confirm_or_abort(app: Application, prompt: str, *, dry_run: bool) -> None:
    """Prompt for confirmation when interactive, aborting if declined; a no-op under dry-run or non-interactive."""
    if not dry_run and app.interactive and not click.confirm(prompt):
        app.abort('Did not get confirmation, aborting.')


def require_github_user(app: Application) -> str:
    """Return the configured GitHub user for branch naming, aborting if none is set."""
    user = app.config.github.user
    if not user:
        app.abort(
            'No GitHub user configured. Set `github.user` via `ddev config set github.user <name>` '
            'or export DD_GITHUB_USER.'
        )
    return user


def _read_commit_subject(app: Application, full_sha: str) -> tuple[str, str | None]:
    """Return (clean_subject, original_pr) for a resolved commit, aborting if it can't be read."""
    log_entries = app.repo.git.log(['hash:%H', 'subject:%s'], n=1, source=full_sha)
    if not log_entries:
        app.abort(f'Could not read commit `{full_sha}`.')
    return split_commit_subject(log_entries[0]['subject'])


def _warn_about_reset_files(app: Application, full_sha: str) -> None:
    """Warn when the commit touches generated files that will be reset to the target branch."""
    reset_files = [
        line
        for line in app.repo.git.capture('diff-tree', '--no-commit-id', '--name-only', '-r', full_sha).splitlines()
        if is_reset_to_target(line)
    ]
    if reset_files:
        listing = '\n  '.join(reset_files)
        app.display_warning(
            f'Commit touches {len(reset_files)} generated file(s) ({RESETTABLE_PATHS_DISPLAY}); they will be '
            f'preserved from the target branch:\n  {listing}'
        )


def build_port_plan(
    app: Application,
    *,
    full_sha: str,
    clean_subject: str,
    original_pr: str | None,
    target_branch: str,
    options: PortOptions,
) -> PortPlan:
    """Assemble a `PortPlan` for an already-resolved commit and a single target branch."""
    user = require_github_user(app)
    suffix = options.branch_suffix or f'to-{target_branch}'
    new_branch = f'{user}/{options.branch_prefix}-{full_sha[:10]}-{suffix}'.lower()
    owner, repo = resolve_owner_repo(app)
    return PortPlan(
        full_sha=full_sha,
        clean_subject=clean_subject,
        original_pr=original_pr,
        target_branch=target_branch,
        new_branch=new_branch,
        worktree_path=_worktree_path_for(app, new_branch),
        pr_title=f'[Backport] {clean_subject}',
        pr_body=build_pr_body(
            app,
            sha=full_sha,
            subject=clean_subject,
            target=target_branch,
            original_pr=original_pr,
            owner=owner,
            repo=repo,
        ),
        labels=parse_labels(options.pr_labels),
        draft=options.draft,
        create_pr=not options.no_pr,
        verify=options.verify,
        dry_run=options.dry_run,
    )


def resolve_port_plan(
    app: Application,
    *,
    commit_hash: str | None,
    target_branch: str,
    options: PortOptions,
) -> PortPlan:
    """Validate inputs, resolve derived values, and confirm with the user. Aborts on failure."""
    require_github_user(app)

    if not options.no_pr and not options.dry_run and not app.config.github.token:
        app.abort(
            'No GitHub token configured. Set `github.token` via `ddev config set github.token <token>` '
            'or export DD_GITHUB_TOKEN. Re-run with `--no-pr` to skip pull request creation.'
        )

    if commit_hash is None:
        head_commit = app.repo.git.latest_commit()
        app.display_info(f'No commit specified. Current HEAD: `{head_commit.sha[:10]}` - {head_commit.subject}')
        confirm_or_abort(app, 'Use this commit?', dry_run=options.dry_run)
        commit_hash = head_commit.sha

    try:
        full_sha = _resolve_input(app, commit_hash, dry_run=options.dry_run)
    except _CommitNotResolvable as exc:
        app.abort(str(exc))

    clean_subject, original_pr = _read_commit_subject(app, full_sha)
    _warn_about_reset_files(app, full_sha)

    plan = build_port_plan(
        app,
        full_sha=full_sha,
        clean_subject=clean_subject,
        original_pr=original_pr,
        target_branch=target_branch,
        options=options,
    )

    app.output(_format_plan_summary(app, plan), stderr=True)

    confirm_or_abort(app, 'Continue?', dry_run=options.dry_run)

    return plan


def display_completion_summary(app: Application, plan: PortPlan, *, pr_url: str | None) -> None:
    """Print a panel summarising the port outcome."""
    rows: list[tuple[str, str]] = [
        ('Commit', f'{plan.full_sha[:10]} - {plan.clean_subject}'),
        ('Target', plan.target_branch),
        ('Branch', plan.new_branch),
    ]
    if pr_url is not None:
        rows.append(('Pull request', pr_url))

    app.output(
        Panel(app.labeled_lines(rows), title='Backport completed', title_align='left', border_style='cyan'),
        stderr=True,
    )


def _format_plan_summary(app: Application, plan: PortPlan) -> Text:
    text = Text()
    text.append('Configuration:', style='bold')

    rows: list[tuple[str, str]] = [
        ('Target branch', plan.target_branch),
        ('Commit', f'{plan.full_sha[:10]} - {plan.clean_subject}'),
        ('Original PR', f'#{plan.original_pr}' if plan.original_pr else '(none)'),
        ('New branch', plan.new_branch),
        ('Worktree path', str(plan.worktree_path)),
        ('Create PR', f'{plan.create_pr} (draft={plan.draft})'),
        ('PR labels', ', '.join(plan.labels) if plan.labels else '(none)'),
        ('Verify commit', str(plan.verify)),
        ('Dry run', str(plan.dry_run)),
    ]
    text.append('\n')
    text.append_text(app.labeled_lines(rows, indent='  ', align=False))
    return text


@dataclass(frozen=True)
class PortStepBundle:
    """All steps produced by `build_port_steps`, separated by lifecycle role.

    `steps` is the ordered sequence the caller iterates and runs. `pr_step` is a
    post-run handle for the PR URL (or `None` when `--no-pr`). `teardown` is the
    worktree-removal step held separately so the caller can skip it on failure,
    leaving the worktree on disk for inspection.
    """

    steps: list[PortStep]
    pr_step: CreatePullRequestStep | None
    teardown: TeardownWorktreeStep


def build_port_steps(app: Application, plan: PortPlan) -> PortStepBundle:
    """Build the workflow steps grouped by lifecycle role."""
    main_git = app.repo.git
    worktree_git = GitRepository(plan.worktree_path)

    steps: list[PortStep] = [
        FetchOriginStep(app, git=main_git, dry_run=plan.dry_run),
        SetupWorktreeStep(
            app,
            main_git=main_git,
            worktree_path=plan.worktree_path,
            branch=plan.new_branch,
            target=plan.target_branch,
            dry_run=plan.dry_run,
        ),
        CherryPickStep(app, git=worktree_git, sha=plan.full_sha, dry_run=plan.dry_run),
        PreserveGeneratedFilesStep(app, git=worktree_git, dry_run=plan.dry_run),
        CommitStep(app, git=worktree_git, subject=plan.clean_subject, verify=plan.verify, dry_run=plan.dry_run),
        PushStep(app, git=worktree_git, branch=plan.new_branch, dry_run=plan.dry_run),
    ]
    pr_step: CreatePullRequestStep | None = None
    if plan.create_pr:
        owner, repo = resolve_owner_repo(app)
        pr_step = CreatePullRequestStep(
            app,
            owner=owner,
            repo=repo,
            title=plan.pr_title,
            head=plan.new_branch,
            base=plan.target_branch,
            body=plan.pr_body,
            labels=plan.labels,
            draft=plan.draft,
            dry_run=plan.dry_run,
        )
        steps.append(pr_step)
    teardown = TeardownWorktreeStep(app, main_git=main_git, worktree_path=plan.worktree_path, dry_run=plan.dry_run)
    return PortStepBundle(steps=steps, pr_step=pr_step, teardown=teardown)


@dataclass(frozen=True)
class PortOutcome:
    """Result of executing a single `PortPlan`. `error` is `None` on success."""

    error: str | None
    pr_url: str | None


def execute_port_plan(app: Application, plan: PortPlan) -> PortOutcome:
    """Run one resolved plan end to end without aborting.

    On failure the worktree is left in place (with a warning) for inspection; on success it is torn
    down. Returns the outcome so the caller decides whether to abort (single-commit path) or move on
    to the next base (`--from-pr`).
    """
    bundle = build_port_steps(app, plan)
    success = False
    error_msg: str | None = None
    try:
        for step in bundle.steps:
            step.run()
        success = True
    except PortStepError as e:
        error_msg = str(e)
    finally:
        # If the PR was created before the failure (e.g. labeling failed afterwards), the worktree
        # holds no recoverable state — the work is pushed and the PR exists on GitHub. Suppress the
        # warning in that case to avoid a misleading "inspect the worktree" message.
        pr_already_created = bundle.pr_step is not None and bundle.pr_step.pr_url is not None
        if not success and not plan.dry_run and not pr_already_created:
            app.display_warning(f'Worktree left at `{plan.worktree_path}` for inspection.')

    pr_url = bundle.pr_step.pr_url if bundle.pr_step is not None else None
    if error_msg is not None:
        return PortOutcome(error=error_msg, pr_url=pr_url)

    try:
        bundle.teardown.run()
    except PortStepError as e:
        app.display_warning(f'Could not remove worktree at `{plan.worktree_path}`: {e}')
        app.display_warning(f'Run `git worktree remove --force {plan.worktree_path}` to clean it up manually.')
    return PortOutcome(error=None, pr_url=pr_url)


class BackportStatus(StrEnum):
    PORTED = auto()
    PLANNED = auto()
    SKIPPED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class BackportResult:
    """Outcome of porting one base. `detail` holds the PR URL (ported), the error text (failed), or None."""

    base: str
    status: BackportStatus
    detail: str | None = None


def run_backport_from_pr(
    app: Application,
    *,
    pr_number: int,
    override_base: str | None,
    options: PortOptions,
) -> bool:
    """Backport a merged PR to each of its `backport/<base>` labels.

    Resolves the PR's squash-merge commit once, derives the target branches from its
    `backport/<base>` labels (or the single `override_base` when one was given), and ports to each. A
    base whose backport PR already exists in any state (open, merged, or closed) is skipped so re-runs
    are idempotent. Returns True when every base succeeded or was skipped.
    """
    if options.branch_suffix is not None and override_base is None:
        app.abort(
            '`--branch-suffix` cannot be combined with `--from-pr` unless `--target-branch` is also '
            'given: the suffix is shared across every derived base, so all bases would resolve to the '
            'same head branch and only the first would be ported. Pass `--target-branch` to port to a '
            'single base, or drop `--branch-suffix` to use the per-base `to-<base>` default.'
        )
    require_github_user(app)

    try:
        pr, full_sha = _resolve_pr(
            app,
            pr_number,
            dry_run=options.dry_run,
            missing_token_message=(
                '`--from-pr` needs a GitHub token to read the pull request. Set `github.token` via '
                '`ddev config set github.token <token>` or export DD_GITHUB_TOKEN.'
            ),
        )
    except _PRNotFound:
        app.abort(f'PR #{pr_number} not found.')
    except _CommitNotResolvable as exc:
        app.abort(str(exc))

    bases = [override_base] if override_base is not None else derive_backport_bases(pr)
    if not bases:
        app.display_warning(f'PR #{pr_number} has no `{BACKPORT_LABEL_PREFIX}<base>` labels; nothing to backport.')
        return True

    clean_subject, original_pr = _read_commit_subject(app, full_sha)
    _warn_about_reset_files(app, full_sha)
    app.display_info(f'Backporting PR #{pr_number} (`{full_sha[:10]}` - {clean_subject}) to: {", ".join(bases)}')

    results = _port_to_each_base(
        app,
        bases=bases,
        full_sha=full_sha,
        clean_subject=clean_subject,
        original_pr=original_pr,
        options=options,
    )
    _display_backport_summary(app, pr_number, results)
    return all(result.status is not BackportStatus.FAILED for result in results)


def _port_to_each_base(
    app: Application,
    *,
    bases: list[str],
    full_sha: str,
    clean_subject: str,
    original_pr: str | None,
    options: PortOptions,
) -> list[BackportResult]:
    """Port one resolved commit to each base in turn, skipping bases that already have a backport PR."""
    owner, repo = resolve_owner_repo(app)
    results: list[BackportResult] = []
    for base in bases:
        plan = build_port_plan(
            app,
            full_sha=full_sha,
            clean_subject=clean_subject,
            original_pr=original_pr,
            target_branch=base,
            options=options,
        )
        if not options.dry_run and _backport_pr_exists(app, owner, repo, plan.new_branch):
            app.display_info(f'Backport to `{base}` already has a PR (branch `{plan.new_branch}`); skipping.')
            results.append(BackportResult(base=base, status=BackportStatus.SKIPPED))
            continue

        app.output(Text(f'Backporting to `{base}`', style='bold'), stderr=True)
        outcome = execute_port_plan(app, plan)
        if outcome.error is None:
            status = BackportStatus.PLANNED if options.dry_run else BackportStatus.PORTED
            results.append(BackportResult(base=base, status=status, detail=outcome.pr_url))
        else:
            app.display_error(f'Backport to `{base}` failed: {outcome.error}')
            results.append(BackportResult(base=base, status=BackportStatus.FAILED, detail=outcome.error))
    return results


def _backport_pr_exists(app: Application, owner: str, repo: str, branch: str) -> bool:
    """Whether a backport PR (any state) already exists for the deterministic `branch`.

    Checks `state=all` so an already-merged backport (whose head branch GitHub deleted) still counts,
    keeping re-runs idempotent. A stale branch from a failed run that never opened a PR is not
    detected here; that surfaces later as a loud non-fast-forward push failure for the operator to
    resolve, rather than a silent branch deletion.

    The lookup filters on `head={owner}:{branch}`, which matches only because the backport branch is
    pushed to `origin` (the same repo `resolve_owner_repo` returns), as `PushStep` does. A fork-based
    push flow would break this match and silently stop detecting existing PRs.
    """
    import asyncio

    import httpx
    from pydantic import ValidationError

    try:
        exists = asyncio.run(_any_pr_for_head(app.config.github.token, owner, repo, branch))
    except (httpx.HTTPError, ValidationError) as exc:
        app.abort(f'Failed to check for an existing backport PR on `{branch}`: {exc}.')
    return exists


async def _any_pr_for_head(token: str, owner: str, repo: str, branch: str) -> bool:
    from ddev.utils.github_async import async_github_client

    async with async_github_client(token=token) as client:
        response = await client.list_pull_requests(owner=owner, repo=repo, state='all', head=f'{owner}:{branch}')
        return len(response.data) > 0


def _display_backport_summary(app: Application, pr_number: int, results: list[BackportResult]) -> None:
    """Print a panel summarising the per-base backport outcomes."""
    icons = {
        BackportStatus.PORTED: '✅',
        BackportStatus.PLANNED: '📋',
        BackportStatus.SKIPPED: '⏭️',
        BackportStatus.FAILED: '❌',
    }
    rows: list[tuple[str, str]] = []
    for result in results:
        label = f'{icons[result.status]} {result.status}'
        if result.detail:
            label = f'{label} - {result.detail}'
        rows.append((result.base, label))
    app.output(
        Panel(
            app.labeled_lines(rows),
            title=f'Backport summary for PR #{pr_number}',
            title_align='left',
            border_style='cyan',
        ),
        stderr=True,
    )
