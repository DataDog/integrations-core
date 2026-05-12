# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


PR_NUMBER_SUFFIX_PATTERN = re.compile(r'\s*\(#(\d+)\)\s*$')
PR_TEMPLATE_RELATIVE_PATH = '.github/PULL_REQUEST_TEMPLATE.md'
PR_TEMPLATE_HEADING = '### What does this PR do?'
IN_TOTO_SUFFIX = '.in-toto'


class PortStepError(Exception):
    """Raised by a PortStep to signal a clean abort with a user-facing message."""


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

        with self.app.status(self.describe()):
            try:
                self.execute()
            except PortStepError:
                raise
            except OSError as e:
                raise PortStepError(str(e)) from e

        self.app.display_success(f'{self.describe()}: done.')


class FetchOriginStep(PortStep):
    def describe(self) -> str:
        return 'Fetching latest changes from origin'

    def planned_commands(self) -> list[str]:
        return ['git fetch origin']

    def execute(self) -> None:
        self.app.repo.git.run('fetch', 'origin')


class CheckoutTargetStep(PortStep):
    def __init__(self, app: Application, *, target: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.target = target

    def describe(self) -> str:
        return f'Checking out and updating `{self.target}`'

    def planned_commands(self) -> list[str]:
        return [f'git checkout {self.target}', f'git pull origin {self.target}']

    def execute(self) -> None:
        self.app.repo.git.run('checkout', self.target)
        self.app.repo.git.run('pull', 'origin', self.target)


class CreatePortBranchStep(PortStep):
    def __init__(self, app: Application, *, branch: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.branch = branch

    def describe(self) -> str:
        return f'Creating branch `{self.branch}`'

    def planned_commands(self) -> list[str]:
        return [f'git checkout -B {self.branch}']

    def execute(self) -> None:
        self.app.repo.git.run('checkout', '-B', self.branch)


class CherryPickStep(PortStep):
    """Cherry-pick a commit, auto-resolving `.in-toto`-only conflicts."""

    def __init__(self, app: Application, *, sha: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.sha = sha

    def describe(self) -> str:
        return f'Cherry-picking {self.sha[:10]}'

    def planned_commands(self) -> list[str]:
        return [f'git cherry-pick --no-commit {self.sha}']

    def execute(self) -> None:
        try:
            self.app.repo.git.run('cherry-pick', '--no-commit', self.sha)
            return
        except OSError:
            pass

        conflicts = [
            line for line in self.app.repo.git.capture('diff', '--name-only', '--diff-filter=U').splitlines() if line
        ]
        non_in_toto = [f for f in conflicts if IN_TOTO_SUFFIX not in f]
        in_toto = [f for f in conflicts if IN_TOTO_SUFFIX in f]

        if non_in_toto:
            try:
                self.app.repo.git.run('cherry-pick', '--abort')
            except OSError:
                pass
            listing = '\n  '.join(non_in_toto)
            raise PortStepError(f'Cherry-pick has conflicts in non-`.in-toto` files:\n  {listing}')

        if not in_toto:
            raise PortStepError('Cherry-pick failed without conflicts. Resolve manually and try again.')

        for path in in_toto:
            _resolve_in_toto_conflict(self.app, path)


class PreserveInTotoStep(PortStep):
    """Reset any staged `.in-toto` changes to keep the target branch's signature metadata."""

    def describe(self) -> str:
        return 'Preserving `.in-toto` files from target branch'

    def planned_commands(self) -> list[str]:
        return ['# Reset any staged .in-toto changes to HEAD']

    def execute(self) -> None:
        staged = [line for line in self.app.repo.git.capture('diff', '--cached', '--name-only').splitlines() if line]
        affected = [f for f in staged if IN_TOTO_SUFFIX in f]
        if not affected:
            return

        for path in affected:
            _restore_path_from_head(self.app, path)


class CommitStep(PortStep):
    def __init__(self, app: Application, *, subject: str, verify: bool = False, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
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
        self.app.repo.git.run(*args)


class PushStep(PortStep):
    def __init__(self, app: Application, *, branch: str, dry_run: bool = False) -> None:
        super().__init__(app, dry_run=dry_run)
        self.branch = branch

    def describe(self) -> str:
        return f'Pushing `{self.branch}` to origin'

    def planned_commands(self) -> list[str]:
        return [f'git push origin {self.branch}']

    def execute(self) -> None:
        self.app.repo.git.run('push', 'origin', self.branch)


class CreatePullRequestStep(PortStep):
    def __init__(
        self,
        app: Application,
        *,
        title: str,
        head: str,
        base: str,
        body: str,
        labels: list[str],
        draft: bool,
        dry_run: bool = False,
    ) -> None:
        super().__init__(app, dry_run=dry_run)
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
        return [f'POST /repos/.../pulls (head={self.head}, base={self.base}{draft_part}){label_part}']

    def execute(self) -> None:
        self.pr_url = self.app.github.create_pull_request(
            title=self.title,
            head=self.head,
            base=self.base,
            body=self.body,
            draft=self.draft,
            labels=self.labels or None,
        )


def _resolve_in_toto_conflict(app: Application, path: str) -> None:
    try:
        app.repo.git.capture('cat-file', '-e', f'HEAD:{path}')
        app.repo.git.run('checkout', '--ours', path)
        app.repo.git.run('add', path)
    except OSError:
        app.repo.git.run('rm', '--force', path)


def _restore_path_from_head(app: Application, path: str) -> None:
    try:
        app.repo.git.capture('cat-file', '-e', f'HEAD:{path}')
        app.repo.git.run('checkout', 'HEAD', '--', path)
    except OSError:
        app.repo.git.run('rm', '--force', path)


def split_commit_subject(subject: str) -> tuple[str, str | None]:
    """Return (subject_without_pr_suffix, original_pr_number_or_None)."""
    match = PR_NUMBER_SUFFIX_PATTERN.search(subject)
    if not match:
        return subject, None
    return PR_NUMBER_SUFFIX_PATTERN.sub('', subject), match.group(1)


def build_pr_body(app: Application, *, sha: str, subject: str, target: str, original_pr: str | None) -> str:
    info_lines = [f'**Backported commit**: `{sha[:10]}` - {subject}']
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


@dataclass(frozen=True)
class PortPlan:
    """All values needed to execute the port workflow, resolved up front."""

    full_sha: str
    clean_subject: str
    original_pr: str | None
    target_branch: str
    new_branch: str
    pr_title: str
    pr_body: str
    labels: list[str]
    draft: bool
    create_pr: bool
    verify: bool
    dry_run: bool


def resolve_port_plan(
    app: Application,
    *,
    commit_hash: str | None,
    target_branch: str,
    branch_prefix: str,
    branch_suffix: str | None,
    pr_labels: str,
    no_pr: bool,
    draft: bool,
    verify: bool,
    dry_run: bool,
) -> PortPlan:
    """Validate inputs, resolve derived values, and confirm with the user. Aborts on failure."""
    user = app.config.github.user
    if not user:
        app.abort(
            'No GitHub user configured. Set `github.user` via `ddev config set github.user <name>` '
            'or export DD_GITHUB_USER.'
        )

    if commit_hash is None:
        head_commit = app.repo.git.latest_commit()
        app.display_info(f'No commit specified. Current HEAD: `{head_commit.sha[:10]}` - {head_commit.subject}')
        if not dry_run and not click.confirm('Use this commit?'):
            app.abort('Did not get confirmation, aborting.')
        commit_hash = head_commit.sha

    try:
        full_sha = app.repo.git.capture('rev-parse', '--verify', f'{commit_hash}^{{commit}}').strip()
    except OSError:
        app.abort(f'Commit `{commit_hash}` does not exist.')

    log_entries = app.repo.git.log(['hash:%H', 'subject:%s'], n=1, source=full_sha)
    if not log_entries:
        app.abort(f'Could not read commit `{full_sha}`.')
    clean_subject, original_pr = split_commit_subject(log_entries[0]['subject'])

    in_toto_files = [
        line
        for line in app.repo.git.capture('diff-tree', '--no-commit-id', '--name-only', '-r', full_sha).splitlines()
        if IN_TOTO_SUFFIX in line
    ]
    if in_toto_files:
        listing = '\n  '.join(in_toto_files)
        app.display_warning(
            f'Commit touches {len(in_toto_files)} `.in-toto` file(s); they will be preserved '
            f'from `{target_branch}`:\n  {listing}'
        )

    suffix = branch_suffix or f'to-{target_branch}'
    plan = PortPlan(
        full_sha=full_sha,
        clean_subject=clean_subject,
        original_pr=original_pr,
        target_branch=target_branch,
        new_branch=f'{user}/{branch_prefix}-{full_sha[:10]}-{suffix}',
        pr_title=f'[Backport] {clean_subject}',
        pr_body=build_pr_body(app, sha=full_sha, subject=clean_subject, target=target_branch, original_pr=original_pr),
        labels=parse_labels(pr_labels),
        draft=draft,
        create_pr=not no_pr,
        verify=verify,
        dry_run=dry_run,
    )

    app.display_info(_format_plan_summary(plan))

    if not dry_run and not click.confirm('Continue?'):
        app.abort('Did not get confirmation, aborting.')

    return plan


def _format_plan_summary(plan: PortPlan) -> str:
    original_pr_line = f'  Original PR: #{plan.original_pr}' if plan.original_pr else '  Original PR: (none)'
    return '\n'.join(
        [
            'Configuration:',
            f'  Target branch: {plan.target_branch}',
            f'  Commit: {plan.full_sha[:10]} - {plan.clean_subject}',
            original_pr_line,
            f'  New branch: {plan.new_branch}',
            f'  Create PR: {plan.create_pr} (draft={plan.draft})',
            f'  PR labels: {", ".join(plan.labels) if plan.labels else "(none)"}',
            f'  Verify commit: {plan.verify}',
            f'  Dry run: {plan.dry_run}',
        ]
    )


def build_port_steps(app: Application, plan: PortPlan) -> tuple[list[PortStep], CreatePullRequestStep | None]:
    """Build the ordered list of steps for the workflow, plus the PR step reference (or None)."""
    steps: list[PortStep] = [
        FetchOriginStep(app, dry_run=plan.dry_run),
        CheckoutTargetStep(app, target=plan.target_branch, dry_run=plan.dry_run),
        CreatePortBranchStep(app, branch=plan.new_branch, dry_run=plan.dry_run),
        CherryPickStep(app, sha=plan.full_sha, dry_run=plan.dry_run),
        PreserveInTotoStep(app, dry_run=plan.dry_run),
        CommitStep(app, subject=plan.clean_subject, verify=plan.verify, dry_run=plan.dry_run),
        PushStep(app, branch=plan.new_branch, dry_run=plan.dry_run),
    ]
    pr_step: CreatePullRequestStep | None = None
    if plan.create_pr:
        pr_step = CreatePullRequestStep(
            app,
            title=plan.pr_title,
            head=plan.new_branch,
            base=plan.target_branch,
            body=plan.pr_body,
            labels=plan.labels,
            draft=plan.draft,
            dry_run=plan.dry_run,
        )
        steps.append(pr_step)
    return steps, pr_step


@click.command(name='port-commit', short_help='Backport a commit onto a target branch')
@click.pass_obj
@click.argument('commit_hash', required=False)
@click.option('-t', '--target-branch', default='master', show_default=True, help='Target branch to port to.')
@click.option('-p', '--branch-prefix', default='port', show_default=True, help='Branch name prefix.')
@click.option('-s', '--branch-suffix', default=None, help='Branch name suffix. Defaults to `to-<target-branch>`.')
@click.option(
    '-l',
    '--pr-labels',
    default='qa/skip-qa',
    show_default=True,
    help='Comma-separated PR labels.',
)
@click.option('--no-pr', is_flag=True, default=False, help="Don't create a pull request.")
@click.option('--draft', is_flag=True, default=False, help='Open the PR as a draft.')
@click.option('--verify', is_flag=True, default=False, help='Run commit hooks (skipped by default).')
@click.option('--dry-run', is_flag=True, default=False, help='Print every step instead of executing it.')
def port_commit(
    app: Application,
    commit_hash: str | None,
    target_branch: str,
    branch_prefix: str,
    branch_suffix: str | None,
    pr_labels: str,
    no_pr: bool,
    draft: bool,
    verify: bool,
    dry_run: bool,
) -> None:
    """
    Backport a commit onto a target branch.

    Cherry-picks COMMIT_HASH onto `--target-branch` (default `master`) on a new branch named
    `<github-user>/<prefix>-<sha[:10]>-<suffix>`, preserving `.in-toto` files from the target
    branch so package signatures stay intact. Pushes the branch and, unless `--no-pr` is set,
    opens a pull request titled `[Backport] <subject>` and labeled with `--pr-labels`.

    If COMMIT_HASH is omitted, the current HEAD commit is used after confirmation.

    The GitHub user for the branch prefix is taken from `ddev config` (`github.user`) or the
    `DD_GITHUB_USER` / `GITHUB_USER` / `GITHUB_ACTOR` environment variables.
    """
    plan = resolve_port_plan(
        app,
        commit_hash=commit_hash,
        target_branch=target_branch,
        branch_prefix=branch_prefix,
        branch_suffix=branch_suffix,
        pr_labels=pr_labels,
        no_pr=no_pr,
        draft=draft,
        verify=verify,
        dry_run=dry_run,
    )
    steps, pr_step = build_port_steps(app, plan)

    try:
        for step in steps:
            step.run()
    except PortStepError as e:
        app.abort(str(e))

    if pr_step is not None and pr_step.pr_url:
        app.display_success(f'Pull request created: {pr_step.pr_url}')
    app.display_success('All done.')
