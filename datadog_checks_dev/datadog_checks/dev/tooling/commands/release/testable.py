# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import random
import time
from typing import List, Optional, Sequence, Set, Tuple

import click

from ....subprocess import SubprocessError, run_command
from ....utils import basepath, chdir, get_next
from ...constants import CHANGELOG_LABEL_PREFIX, CHANGELOG_TYPE_NONE, get_root
from ...github import get_pr, get_pr_from_hash, get_pr_labels, get_pr_milestone, parse_pr_number
from ...jira import JiraClient
from ...utils import format_commit_id
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning


def create_jira_issue(
    client: JiraClient,
    teams: List[str],
    pr_title: str,
    pr_url: str,
    pr_body: str,
    dry_run: bool,
    pr_author: str,
    config: dict,
) -> None:
    body = f'Pull request: {pr_url}\n\n{pr_body}'

    for team in teams:
        member = pick_card_member(config, pr_author, team)
        if member:
            echo_info(f'Randomly assigned issue to {member}')
        if dry_run:
            echo_success(f'Will create an issue for team {team}: ', nl=False)
            echo_info(pr_title)
            continue
        creation_attempts = 3
        for attempt in range(3):
            rate_limited, error, response = client.create_issue(team, pr_title, body, member)
            if rate_limited:
                wait_time = 10
                echo_warning(
                    'Attempt {} of {}: A rate limit in effect, retrying in {} '
                    'seconds...'.format(attempt + 1, creation_attempts, wait_time)
                )
                time.sleep(wait_time)
            elif error:
                if attempt + 1 == creation_attempts:
                    echo_failure(f'Error: {error}')
                    break

                wait_time = 2
                echo_warning(
                    'Attempt {} of {}: An error has occurred, retrying in {} '
                    'seconds...'.format(attempt + 1, creation_attempts, wait_time)
                )
                time.sleep(wait_time)
            else:
                issue_key = response.json().get('key')
                echo_success(f'Created issue {issue_key} for team {team}')
                break


def _all_synced_with_remote(refs: Sequence[str]) -> bool:
    fetch_command = 'git fetch --dry'
    result = run_command(fetch_command, capture=True, check=True)
    return all(ref not in result.stderr for ref in refs)


def _get_and_parse_commits(base_ref: str, target_ref: str) -> List[Tuple[str, str]]:
    echo_info(f'Getting diff between {base_ref!r} and {target_ref!r}... ', nl=False)

    # Format as '<commit_hash> <subject line>', e.g.:
    # 'a70a792f9d1775b7d6d910044522f7a0d6941ad7 Update README.md'
    pretty_format = '%H %s'

    diff_command = f'git --no-pager log "--pretty={pretty_format}" {base_ref}..{target_ref}'

    try:
        result = run_command(diff_command, capture=True, check=True)
    except SubprocessError:
        echo_failure('Failed!')
        raise

    echo_success('Success!')
    lines: List[str] = result.stdout.splitlines()

    commits = []

    for line in reversed(lines):
        commit_hash, _, commit_subject = line.partition(' ')
        commits.append((commit_hash, commit_subject))

    return commits


def get_commits_between(base_ref: str, target_ref: str, *, root: str) -> List[Tuple[str, str]]:
    with chdir(root):
        if not _all_synced_with_remote((base_ref, target_ref)):
            abort(f'Your repository is not sync with the remote repository. Please run `git fetch` in {root!r} folder.')

        try:
            return _get_and_parse_commits(base_ref, target_ref)
        except SubprocessError as exc:
            echo_failure(str(exc))
            echo_failure('Unable to get the diff.')
            echo_info(
                f'HINT: ensure {base_ref!r} and {target_ref!r} both refer to a valid git reference '
                '(such as a tag or a release branch).'
            )
            raise click.Abort


def pick_card_member(config: dict, author: str, team: str) -> Optional[str]:
    """Return a member to assign to the created issue.
    In practice, it returns one jira user which is not the PR author, for the given team.
    For it to work, you need a `jira_users_$team` table in your ddev configuration,
    with keys being github users and values being their corresponding jira IDs (not names).

    For example::
        [jira_users_integrations]
        john = "xxxxxxxxxxxxxxxxxxxxx"
        alice = "yyyyyyyyyyyyyyyyyyyy"
    """
    users = config.get(f'jira_users_{team.lower()}')
    if not users:
        return None
    member = random.choice([key for user, key in users.items() if user != author])
    return member


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help='Create a Jira issue for each change that needs to be tested'
)
@click.argument('base_ref')
@click.argument('target_ref')
@click.option('--milestone', help='The PR milestone to filter by')
@click.option('--dry-run', '-n', is_flag=True, help='Only show the changes')
@click.pass_context
def testable(ctx: click.Context, base_ref: str, target_ref: str, milestone: str, dry_run: bool) -> None:
    """
    Create a Jira issue for changes since a previous release (referenced by BASE_REF)
    that need to be tested for the next release (referenced by TARGET_REF).

    Usage
    -----
    BASE_REF and TARGET_REF can be any valid git references. It practice, you should use either:

    * A tag: `7.16.1`, `7.17.0-rc.4`, ...

    * A release branch: `6.16.x`, `7.17.x`, ...

    * The `master` branch.

    NOTE: using a minor version shorthand (e.g. `7.16`) is not supported, as it is ambiguous.

    Example: assuming we are working on the release of 7.17.0, we can...

    * Create cards for changes between a previous Agent release and `master` (useful when preparing an initial RC):

        $ ddev release testable 7.16.1 origin/master

    * Create cards for changes between a previous RC and `master` (useful when preparing a new RC, and a separate
    release branch was not created yet):

        $ ddev release testable 7.17.0-rc.2 origin/master

    * Create cards for changes between a previous RC and a release branch (useful to only review changes in a
    release branch that has diverged from `master`):

        $ ddev release testable 7.17.0-rc.4 7.17.x

    * Create cards for changes between two arbitrary tags, e.g. between RCs:

        $ ddev release testable 7.17.0-rc.4 7.17.0-rc.5

    TIP: run with `ddev -x release testable` to force the use of the current directory.

    Prerequisites
    -------------
    To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

    \b
    To use Jira:
    1. Go to `https://id.atlassian.com/manage/api-tokens` and create an API token.
    2. Run `ddev config set jira.user` and enter your jira email.
    3. Run `ddev config set jira.token` and paste your API token.
    """
    root = get_root()
    repo = basepath(root)
    if repo not in ('integrations-core', 'datadog-agent'):
        abort(f'Repo `{repo}` is unsupported.')

    commits = get_commits_between(base_ref, target_ref, root=root)
    num_changes = len(commits)

    if not num_changes:
        echo_warning('No changes.')
        return

    if repo == 'integrations-core':
        options = {'1': 'Integrations', '2': 'Containers', '3': 'Core', '4': 'Platform', 's': 'Skip', 'q': 'Quit'}
    else:
        options = {
            '1': 'Core',
            '2': 'Containers',
            '3': 'Logs',
            '4': 'Platform',
            '5': 'Networks',
            '6': 'Processes',
            '7': 'Trace',
            '8': 'Integrations',
            's': 'Skip',
            'q': 'Quit',
        }
    default_option = get_next(options)
    options_prompt = f'Choose an option (default {options[default_option]}): '
    options_text = '\n' + '\n'.join('{} - {}'.format(key, value) for key, value in options.items())

    commit_ids: Set[str] = set()
    user_config = ctx.obj
    jira = JiraClient(user_config)
    for i, (commit_hash, commit_subject) in enumerate(commits, 1):
        commit_id = parse_pr_number(commit_subject)
        if commit_id is not None:
            api_response = get_pr(commit_id, user_config, raw=True)
            if api_response.status_code == 401:
                abort('Access denied. Please ensure your GitHub token has correct permissions.')
            elif api_response.status_code == 403:
                echo_failure(
                    'Error getting info for #{}. Please set a GitHub HTTPS '
                    'token to avoid rate limits.'.format(commit_id)
                )
                continue
            elif api_response.status_code == 404:
                echo_info(f'Skipping #{commit_id}, not a pull request...')
                continue

            api_response.raise_for_status()
            pr_data = api_response.json()
        else:
            try:
                api_response = get_pr_from_hash(commit_hash, repo, user_config, raw=True)
                if api_response.status_code == 401:
                    abort('Access denied. Please ensure your GitHub token has correct permissions.')
                elif api_response.status_code == 403:
                    echo_failure(
                        'Error getting info for #{}. Please set a GitHub HTTPS '
                        'token to avoid rate limits.'.format(commit_hash)
                    )
                    continue

                api_response.raise_for_status()
                pr_data = api_response.json()
                pr_data = pr_data.get('items', [{}])[0]
            # Commit to master
            except IndexError:
                pr_data = {
                    'number': commit_hash,
                    'html_url': f'https://github.com/DataDog/{repo}/commit/{commit_hash}',
                }
            commit_id = str(pr_data.get('number', ''))

        if commit_id and commit_id in commit_ids:
            echo_info(f'Already seen PR #{commit_id}, skipping it.')
            continue
        commit_ids.add(commit_id)

        pr_labels = sorted(get_pr_labels(pr_data))
        documentation_pr = False
        nochangelog_pr = True
        for label in pr_labels:
            if label.startswith('documentation'):
                documentation_pr = True

            if label.startswith(CHANGELOG_LABEL_PREFIX) and label.split('/', 1)[1] != CHANGELOG_TYPE_NONE:
                nochangelog_pr = False

        if documentation_pr and nochangelog_pr:
            echo_info(f'Skipping documentation {format_commit_id(commit_id)}.')
            continue

        pr_milestone = get_pr_milestone(pr_data)
        if milestone and pr_milestone != milestone:
            echo_info(f'Looking for milestone {milestone}, skipping {format_commit_id(commit_id)}.')
            continue

        pr_url = pr_data.get('html_url', f'https://github.com/DataDog/{repo}/pull/{commit_id}')
        pr_title = pr_data.get('title', commit_subject)
        pr_author = pr_data.get('user', {}).get('login', '')
        pr_body = pr_data.get('body', '')

        jira_config = user_config['jira']
        if not (jira_config['user'] and jira_config['token']):
            abort('Error: You are not authenticated for Jira. Please set your jira ddev config')

        teams = [jira.label_team_map[label] for label in pr_labels if label in jira.label_team_map]
        if teams:
            create_jira_issue(jira, teams, pr_title, pr_url, pr_body, dry_run, pr_author, user_config)
            continue

        finished = False
        choice_error = ''
        progress_status = f'({i} of {num_changes}) '
        indent = ' ' * len(progress_status)

        while not finished:
            echo_success(f'\n{progress_status}{pr_title}')

            echo_success('Url: ', nl=False, indent=indent)
            echo_info(pr_url)

            echo_success('Author: ', nl=False, indent=indent)
            echo_info(pr_author)

            echo_success('Labels: ', nl=False, indent=indent)
            echo_info(', '.join(pr_labels))

            if pr_milestone:
                echo_success('Milestone: ', nl=False, indent=indent)
                echo_info(pr_milestone)

            # Ensure Unix lines feeds just in case
            echo_info(pr_body.strip('\r'), indent=indent)

            echo_info(options_text)

            if choice_error:
                echo_warning(choice_error)

            echo_waiting(options_prompt, nl=False)

            # Terminals are odd and sometimes produce an erroneous null byte
            choice = '\x00'
            while choice == '\x00':
                choice = click.getchar().strip()

            if not choice:
                choice = default_option

            if choice not in options:
                echo_info(choice)
                choice_error = f'`{choice}` is not a valid option.'
                continue
            else:
                choice_error = ''

            value = options[choice]
            echo_info(value)

            if value == 'Skip':
                echo_info(f'Skipped {format_commit_id(commit_id)}')
                break
            elif value == 'Quit':
                echo_warning(f'Exited at {format_commit_id(commit_id)}')
                return
            else:
                create_jira_issue(jira, [value], pr_title, pr_url, pr_body, dry_run, pr_author, user_config)

            finished = True
