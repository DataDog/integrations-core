# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import random
import time

import click
from semver import parse_version_info

from ....subprocess import run_command
from ....utils import basepath, chdir, get_next
from ...constants import CHANGELOG_LABEL_PREFIX, CHANGELOG_TYPE_NONE, get_root
from ...github import get_pr, get_pr_from_hash, get_pr_labels, get_pr_milestone, parse_pr_number
from ...jira import JiraClient
from ...utils import format_commit_id, get_current_agent_version
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning


def validate_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    try:
        parts = value.split('.')
        if len(parts) == 2:
            parts.append('0')
        version_info = parse_version_info('.'.join(parts))
        return f'{version_info.major}.{version_info.minor}'
    except ValueError:
        raise click.BadParameter('needs to be in semver format x.y[.z]')


def create_jira_issue(client, teams, pr_title, pr_url, pr_body, dry_run, pr_author, config):
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


def pick_card_member(config, author, team):
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
        return
    member = random.choice([key for user, key in users.items() if user != author])
    return member


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help='Create a Jira issue for each change that needs to be tested'
)
@click.option('--start', 'start_id', help='The PR number or commit hash to start at')
@click.option('--since', 'agent_version', callback=validate_version, help='The version of the Agent to compare')
@click.option('--milestone', help='The PR milestone to filter by')
@click.option('--dry-run', '-n', is_flag=True, help='Only show the changes')
@click.pass_context
def testable(ctx, start_id, agent_version, milestone, dry_run):
    """Create a Jira issue for each change that needs to be tested for
    the next release. Run via `ddev -x release testable` to force the use
    of the current directory.
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

    if agent_version:
        current_agent_version = agent_version
    else:
        echo_waiting('Finding the current minor release of the Agent... ', nl=False)
        current_agent_version = get_current_agent_version()
        echo_success(current_agent_version)

    current_release_branch = f'{current_agent_version}.x'
    diff_target_branch = 'origin/master'
    echo_info(f'Branch `{current_release_branch}` will be compared to `{diff_target_branch}`.')

    echo_waiting('Getting diff... ', nl=False)
    diff_command = 'git --no-pager log "--pretty=format:%H %s" {}..{}'

    with chdir(root):
        fetch_command = 'git fetch --dry'
        result = run_command(fetch_command, capture=True)
        if result.code:
            abort(f'Unable to run {fetch_command}.')

        if current_release_branch in result.stderr or diff_target_branch in result.stderr:
            abort(
                'Your repository is not sync with the remote repository. Please run git fetch in {} folder.'.format(
                    root
                )
            )

        # compare with the local tag first
        reftag = f"{'refs/tags/'}{current_release_branch}"
        result = run_command(diff_command.format(reftag, diff_target_branch), capture=True)
        if result.code:
            # if it didn't work, compare with a branch.
            origin_release_branch = f'origin/{current_release_branch}'
            echo_failure('failed!')
            echo_waiting(
                'Local branch `{}` might not exist, trying `{}`... '.format(
                    current_release_branch, origin_release_branch
                ),
                nl=False,
            )

            result = run_command(diff_command.format(origin_release_branch, diff_target_branch), capture=True)
            if result.code:
                abort('Unable to get the diff.')
            else:
                echo_success('success!')
        else:
            echo_success('success!')

    # [(commit_hash, commit_subject), ...]
    diff_data = [tuple(line.split(None, 1)) for line in reversed(result.stdout.splitlines())]
    num_changes = len(diff_data)

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

    commit_ids = set()
    user_config = ctx.obj
    jira = JiraClient(user_config)
    found_start_id = False

    for i, (commit_hash, commit_subject) in enumerate(diff_data, 1):
        commit_id = parse_pr_number(commit_subject)
        if commit_id:
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

        if start_id and not found_start_id:
            if start_id == commit_id or start_id == commit_hash:
                found_start_id = True
            else:
                echo_info(f'Looking for {format_commit_id(start_id)}, skipping {format_commit_id(commit_id)}.')
                continue

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
