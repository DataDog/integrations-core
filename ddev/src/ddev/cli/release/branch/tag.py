from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import click
from httpx import HTTPStatusError
from packaging.version import Version

from ddev.utils.git import GitRepository
from ddev.utils.github_errors import GitHubAuthenticationError

from .build_agent import BUILD_AGENT_YAML_PATH, find_build_agent_template_main_branch_matches
from .create import BRANCH_NAME_REGEX

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.utils.github import PullRequest

UPDATE_BUILD_AGENT_YAML_WORKFLOW = 'update-build-agent-yaml.yml'
# The dd-octo-sts policy grants PR-writing credentials only to this workflow on master.
UPDATE_BUILD_AGENT_YAML_WORKFLOW_REF = 'master'
RELEASE_INPUT_REGEX = re.compile(r'^(\d+\.\d+)(\.x)?$')
# Sentinel used by `--rc` when the user provides the flag without a value.
# Chosen so that `--rc auto` (which users could plausibly type) is rejected by `_parse_rc_value`
# rather than silently treated as bare `--rc`.
RC_AUTO = '__rc_auto_sentinel__'


@click.command
@click.option(
    '--release',
    '-r',
    'release',
    default=None,
    help=(
        'Release to tag, e.g. `7.56` or `7.56.x`. '
        'If omitted, the current branch must be a release branch and you will be prompted to confirm.'
    ),
)
@click.option(
    '--ref',
    'ref',
    default=None,
    help=(
        'Commit (SHA, tag, or ref) to tag instead of the tip of the release branch. '
        'Must resolve to a commit that is an ancestor of `origin/<release-branch>`.'
    ),
)
@click.option(
    '--final',
    'final',
    is_flag=True,
    default=False,
    help='Tag a final release. Mutually exclusive with `--rc`.',
)
@click.option(
    '--rc',
    'rc',
    is_flag=False,
    flag_value=RC_AUTO,
    default=None,
    help=(
        'Tag a release candidate (default). Pass `--rc` alone to auto-suggest the next RC number, '
        'or `--rc N` to pin the RC number explicitly. Mutually exclusive with `--final`.'
    ),
)
@click.option(
    '--yes',
    '-y',
    'yes',
    is_flag=True,
    default=False,
    help='Skip yes/no confirmation prompts and assume the user always answered yes.',
)
@click.option(
    '--skip-open-pr-check',
    is_flag=True,
    default=False,
    show_default=True,
    help='Skip checking GitHub for open PRs targeting this release branch before tagging.',
)
@click.pass_obj
def tag(
    app: Application,
    release: str | None,
    ref: str | None,
    final: bool,
    rc: str | None,
    yes: bool,
    skip_open_pr_check: bool,
) -> None:
    """
    Tag a release branch with a release-candidate or final-release tag.

    The command always operates against `origin/<release-branch>` after fetching: it does not
    check out or modify any local branch. The release branch is determined as follows:

    \b
    - If `--release` is given (e.g. `7.56` or `7.56.x`), that branch is used.
    - If `--release` is omitted and you are on a release branch, you are prompted to confirm
      tagging that branch (use `--yes` to skip the prompt).
    - If `--release` is omitted and you are not on a release branch, the command aborts and
      asks you to pass `--release`.

    Tag-type selection:

    \b
    - `--rc` (default) tags a release candidate. Pass `--rc N` to pin the RC number; pass
      `--rc` alone to auto-suggest the next available RC. The command warns (but does not
      abort) if the requested number leaves a gap in the RC sequence.
    - `--final` tags a final release; mutually exclusive with `--rc`.

    Other options:

    \b
    - `--ref <commit>` tags an arbitrary commit instead of the branch tip. The commit must be
      an ancestor of `origin/<release-branch>`. Useful when later commits should not be
      included in the tag.
    - `--yes/-y` skips all yes/no confirmations (target-branch, backward-RC, final tag).
    - `--skip-open-pr-check` skips the GitHub query for open PRs targeting the branch.
    """
    if final and rc is not None:
        raise click.UsageError('`--final` and `--rc` are mutually exclusive.')
    is_rc = not final
    pinned_rc = _parse_rc_value(rc) if is_rc else None

    current_branch = app.repo.git.current_branch()
    target_branch = _resolve_target_branch(app, release, yes, current_branch)

    git = app.repo.git
    app.display_waiting('Fetching from origin...')
    git.fetch_tags()
    _ensure_branch_on_origin(app, git, target_branch)

    tag_ref = _resolve_tag_ref(app, git, target_branch, ref)
    effective_ref = tag_ref if tag_ref is not None else f'origin/{target_branch}'

    build_agent_yaml_needs_update = _warn_if_build_agent_yaml_stale(app, git, effective_ref)
    new_tag = _compute_new_tag(app, git, target_branch, is_rc, pinned_rc, yes)
    _confirm_and_push_tag(app, git, target_branch, new_tag, tag_ref, effective_ref, yes, skip_open_pr_check)

    if build_agent_yaml_needs_update:
        _trigger_build_agent_yaml_update_workflow(app, target_branch)


def _warn_if_build_agent_yaml_stale(app: Application, git: GitRepository, ref: str) -> bool:
    """Warn (and return True) if `.gitlab/build_agent.yaml` at `ref` still points to `main`."""
    if not _build_agent_yaml_points_to_main(git, ref):
        return False
    # Recovery path for release branches cut before build_agent.yaml was updated.
    app.display_warning(
        "`.gitlab/build_agent.yaml` still points to `main`.\n"
        "The update PR may not have been created or merged yet.\n"
        "Will trigger the workflow after the tag is pushed.\n"
        "Tagging will continue."
    )
    return True


def _compute_new_tag(
    app: Application,
    git: GitRepository,
    target_branch: str,
    is_rc: bool,
    pinned_rc: int | None,
    yes: bool,
) -> str:
    """Compute the new tag string, validating RC bounds, existence, gaps, and backward moves."""
    major_minor_version = target_branch.replace('.x', '')
    this_release_tags = sorted(
        (
            Version(t)
            for t in set(git.tags(glob_pattern=major_minor_version + '.*'))
            # We take 'major.minor.x' as the branch name pattern and replace 'x' with 'patch-rc.number'.
            # We make the RC component optional so that final tags also match our filter.
            if re.match(BRANCH_NAME_REGEX.pattern.replace('x', r'\d+(\-rc\.\d+)?'), t)
        ),
        reverse=True,
    )
    last_patch, last_rc = _extract_patch_and_rc(this_release_tags)
    last_tag_was_final = last_rc is None
    new_patch = last_patch + 1 if last_tag_was_final else last_patch
    new_tag = f'{major_minor_version}.{new_patch}'
    if not is_rc:
        return new_tag

    new_rc_guess = 1 if last_tag_was_final else last_rc + 1
    if pinned_rc is not None:
        next_rc = pinned_rc
    elif yes:
        next_rc = new_rc_guess
        click.echo(f'Using auto-suggested RC number: {next_rc}')
    else:
        next_rc = click.prompt(
            'What RC number are we tagging? (hit ENTER to accept suggestion)',
            type=int,
            default=new_rc_guess,
        )
    if next_rc < 1:
        # Only reachable for the interactive prompt — `--rc N` is validated up-front in
        # `_parse_rc_value`.
        app.abort('RC number must be at least 1.')
    new_tag += f'-rc.{next_rc}'
    if Version(new_tag) in this_release_tags:
        app.abort(f'Tag {new_tag} already exists. Switch to git to overwrite it.')
    _warn_on_rc_gap(app, next_rc, new_rc_guess, target_branch)
    if not last_tag_was_final and next_rc < last_rc:
        click.secho('!!! WARNING !!!')
        if not _confirm(
            yes,
            f'The latest RC is {last_rc}. '
            'You are about to go back in time by creating an RC with a number less than that. Are you sure? '
            '[y/N]',
        ):
            app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    return new_tag


def _confirm_and_push_tag(
    app: Application,
    git: GitRepository,
    target_branch: str,
    new_tag: str,
    tag_ref: str | None,
    effective_ref: str,
    yes: bool,
    skip_open_pr_check: bool,
) -> None:
    """Surface open-PR warnings, get final confirmation, then create and push the tag.

    `tag_ref` is the user-resolved commit when `--ref` was explicitly provided (used for the
    "at <sha>?" prompt suffix). `effective_ref` is what `git tag` actually keys off — either
    that same commit, or `origin/<target_branch>` when `--ref` was not supplied.
    """
    prs = _check_open_prs(app, target_branch, skip_open_pr_check)

    prompt = f'Create and push this tag: {new_tag}?'
    if prs:
        prompt = f'Open PRs found targeting {target_branch}. Create and push this tag anyway: {new_tag}?'
    if tag_ref is not None:
        prompt = prompt.rstrip('?') + f' at {tag_ref}?'

    if not _confirm(yes, prompt):
        app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    try:
        click.echo(git.tag(new_tag, message=new_tag, ref=effective_ref))
        click.echo(git.push(new_tag))
    except OSError as e:
        app.abort(f'Failed to create or push tag `{new_tag}`: {e}')


def _parse_rc_value(rc: str | None) -> int | None:
    if rc is None or rc == RC_AUTO:
        return None
    try:
        value = int(rc)
    except ValueError as e:
        raise click.UsageError(f'`--rc` value must be a positive integer, got `{rc}`.') from e
    if value < 1:
        raise click.UsageError(f'`--rc` value must be a positive integer, got `{rc}`.')
    return value


def _resolve_target_branch(app: Application, release: str | None, yes: bool, current_branch: str) -> str:
    if release is not None:
        match = RELEASE_INPUT_REGEX.match(release)
        if match is None:
            raise click.UsageError(f'Invalid `--release` value: `{release}`. Must look like `7.56` or `7.56.x`.')
        return f'{match.group(1)}.x'

    if BRANCH_NAME_REGEX.match(current_branch) is None:
        app.abort(
            f'Current branch `{current_branch}` is not a release branch. '
            f'Pass `--release <X.Y[.x]>` to choose the release branch to tag.'
        )

    if not _confirm(yes, f'You are on release branch `{current_branch}`. Tag this release?'):
        app.abort('Did not get confirmation, aborting. Did not create or push the tag.')
    return current_branch


def _ensure_branch_on_origin(app: Application, git: GitRepository, branch: str) -> None:
    try:
        output = git.capture('ls-remote', '--heads', 'origin', branch)
    except OSError as e:
        app.abort(f'Failed to query `origin` for branch `{branch}`: {e}')
    if not any(line.strip() for line in output.splitlines()):
        app.abort(f'Release branch `{branch}` does not exist on `origin`.')


def _resolve_tag_ref(app: Application, git: GitRepository, target_branch: str, ref: str | None) -> str | None:
    if ref is None:
        return None
    commit_sha: str | None = None
    try:
        commit_sha = git.capture('rev-parse', '--verify', f'{ref}^{{commit}}').strip()
        git.capture('merge-base', '--is-ancestor', commit_sha, f'origin/{target_branch}')
    except OSError as e:
        if commit_sha is None:
            app.abort(f'`--ref` value `{ref}` does not resolve to a commit: {e}')
        app.abort(
            f'`--ref` value `{ref}` (resolved to `{commit_sha}`) is not an ancestor of '
            f'`origin/{target_branch}` (or `git merge-base` itself failed): {e}'
        )
    return commit_sha


def _warn_on_rc_gap(app: Application, next_rc: int, expected_rc: int, branch: str) -> None:
    if next_rc <= expected_rc:
        return
    missing = list(range(expected_rc, next_rc))
    missing_list = ', '.join(str(n) for n in missing)
    suggested_rc = missing[0]
    app.display_warning(
        f'Requested RC {next_rc} skips ahead of the next available RC ({expected_rc}). '
        f'Missing RC number(s): {missing_list}.\n'
        f'To fill the gap later, run: '
        f'ddev release branch tag --release {branch} --rc {suggested_rc} --ref <commit>'
    )


def _check_open_prs(app: Application, target_branch: str, skip_open_pr_check: bool) -> list[PullRequest]:
    if skip_open_pr_check:
        return []
    httpx_logger = logging.getLogger('httpx')
    previous_level = httpx_logger.level
    httpx_logger.setLevel(logging.WARNING)
    try:
        prs = app.github.list_open_pull_requests_targeting_base(target_branch)
    except GitHubAuthenticationError:
        raise
    except Exception as e:
        click.secho(f'Warning: unable to check for open PRs: {e}', fg='yellow')
        return []
    finally:
        httpx_logger.setLevel(previous_level)

    if prs:
        click.secho('!!! WARNING !!!', fg='yellow')
        click.secho(f'Found {len(prs)} open PR(s) targeting base branch {target_branch}:', fg='yellow')
        for pr in prs[:20]:
            click.secho(f'  - #{pr.number} {pr.title} ({pr.html_url})', fg='yellow')
        if len(prs) > 20:
            click.secho(f'  ... and {len(prs) - 20} more', fg='yellow')
    return prs


def _confirm(yes: bool, prompt: str) -> bool:
    if yes:
        click.echo(f'{prompt} [auto-yes]')
        return True
    return click.confirm(prompt)


def _build_agent_yaml_points_to_main(git: GitRepository, ref: str) -> bool:
    try:
        content = git.show_file(BUILD_AGENT_YAML_PATH, ref)
    except OSError:
        return False
    return bool(find_build_agent_template_main_branch_matches(content))


def _trigger_build_agent_yaml_update_workflow(app: Application, branch_name: str) -> None:
    try:
        app.github.dispatch_workflow(
            UPDATE_BUILD_AGENT_YAML_WORKFLOW,
            UPDATE_BUILD_AGENT_YAML_WORKFLOW_REF,
            {'branch': branch_name},
        )
    except GitHubAuthenticationError:
        app.display_warning(
            f'The tag was pushed, but `{UPDATE_BUILD_AGENT_YAML_WORKFLOW}` could not be triggered.\n'
            f'To trigger it manually: gh workflow run {UPDATE_BUILD_AGENT_YAML_WORKFLOW} -f branch={branch_name}'
        )
        raise
    except HTTPStatusError as e:
        app.display_warning(
            f'Warning: unable to trigger `{UPDATE_BUILD_AGENT_YAML_WORKFLOW}`: {e}\n'
            f'To trigger it manually: gh workflow run {UPDATE_BUILD_AGENT_YAML_WORKFLOW} -f branch={branch_name}'
        )
    else:
        app.display_success(
            f'Dispatched `{UPDATE_BUILD_AGENT_YAML_WORKFLOW}`; check the workflow run for PR creation status.'
        )


def _extract_patch_and_rc(version_tags):
    if not version_tags:
        return 0, 0
    latest = version_tags[0]
    patch = latest.micro
    # latest.pre is None for final releases and a tuple ('rc', <NUM>) for RC.
    rc = latest.pre if latest.pre is None else latest.pre[1]
    return patch, rc
