# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, cast

import click

from .....fs import basepath, chdir
from .....subprocess import SubprocessError, run_command
from .....utils import get_next
from ....config import APP_DIR
from ....constants import CHANGELOG_LABEL_PREFIX, CHANGELOG_TYPE_NONE, get_root
from ....github import get_pr, get_pr_from_hash, get_pr_labels, get_pr_milestone, parse_pr_number
from ....trello import TrelloClient
from ....utils import format_commit_id
from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning
from .fixed_cards_mover import FixedCardsMover
from .rc_build_cards_updater import RCBuildCardsUpdater
from .tester_selector.tester_selector import TesterSelector, TrelloUser, create_tester_selector


def create_trello_card(
    client: TrelloClient,
    testerSelector: TesterSelector,
    teams: List[str],
    pr_num: int,
    pr_title: str,
    pr_url: str,
    pr_labels: List[str],
    pr_body: str,
    dry_run: bool,
    pr_author: str,
    config: dict,
    card_assignments: dict,
) -> None:
    labels = ', '.join(f'`{label}`' for label in sorted(pr_labels))
    body = f'''\
Pull request: {pr_url}
Author: `{pr_author}`
Labels: {labels}

{pr_body}'''
    for team in teams:
        tester_name, member = pick_card_member(config, pr_author, team.lower(), card_assignments)
        if member is None:
            tester = _select_trello_tester(client, testerSelector, team, pr_author, pr_num, pr_url)
            if tester:
                member = tester.id
                tester_name = tester.full_name

        if dry_run:
            echo_success(f'Will create a card for {tester_name}: ', nl=False)
            echo_info(pr_title)
            continue
        creation_attempts = 3
        for attempt in range(3):
            rate_limited, error, response = client.create_card(team, pr_title, body, member)
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
                echo_success(f'Created card for team {team}: ', nl=False)
                echo_info(response.json().get('url'))
                break


def _select_trello_tester(
    trello: TrelloClient, testerSelector: TesterSelector, team: str, pr_author: str, pr_num: int, pr_url: str
) -> Optional[TrelloUser]:
    team_label = None
    for label, t in trello.label_team_map.items():
        if t == team:
            team_label = label
            break

    trello_user = None
    if team_label in trello.label_github_team_map:
        github_team = trello.label_github_team_map[team_label]
        if pr_author:
            trello_user = testerSelector.get_next_tester(pr_author, github_team, pr_num)
    else:
        echo_warning(f'Invalid team {team} for {pr_url}')

    if not trello_user:
        echo_warning(f'Cannot assign tester for {pr_author} {pr_url}')
        return None
    return trello_user


def _all_synced_with_remote(refs: Sequence[str]) -> bool:
    fetch_command = 'git fetch --dry'
    result = run_command(fetch_command, capture=True, check=True)
    return all(ref not in result.stderr for ref in refs)


def _get_and_parse_commits(base_ref: str, target_ref: str) -> List[Tuple[str, str]]:
    echo_info(f'Getting diff between {base_ref!r} and {target_ref!r}... ', nl=False)

    # Outputs as '<sign> <commit_hash> <subject line>', e.g.:
    # '+ 32837dac944b9dcc23d6b54370657d661226c3ac Update README.md (#8778)'
    diff_command = f'git --no-pager cherry -v {base_ref} {target_ref}'

    try:
        result = run_command(diff_command, capture=True, check=True)
    except SubprocessError:
        echo_failure('Failed!')
        raise

    echo_success('Success!')
    lines: List[str] = result.stdout.splitlines()

    commits = []
    for line in reversed(lines):
        sign, commit_hash, commit_subject = line.split(' ', 2)
        if sign == '-':
            echo_info(f'Skipping {commit_subject}, it was cherry-picked in {base_ref}')
            continue
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


def pick_card_member(config: dict, author: str, team: str, card_assignments: dict) -> Tuple[Any, Any]:
    """Return a member to assign to the created issue.
    In practice, it returns one trello user which is not the PR author, for the given team.
    For it to work, you need a `trello_users_$team` table in your ddev configuration,
    with keys being github users and values being their corresponding trello IDs (not names).

    For example::
        [trello_users_integrations]
        john = "xxxxxxxxxxxxxxxxxxxxx"
        alice = "yyyyyyyyyyyyyyyyyyyy"
    """
    users = config.get(f'trello_users_{team}')
    if not users:
        return None, None
    if team not in card_assignments:
        # initialize map team -> user -> QA cards assigned
        team_members = list(users)
        random.shuffle(team_members)
        card_assignments[team] = dict.fromkeys(team_members, 0)

    member = min([member for member in card_assignments[team] if member != author], key=card_assignments[team].get)
    card_assignments[team][member] += 1
    return member, users[member]


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help='Create a Trello card for each change that needs to be tested'
)
@click.argument('base_ref')
@click.argument('target_ref')
@click.option('--milestone', help='The PR milestone to filter by')
@click.option('--dry-run', '-n', is_flag=True, help='Only show the changes')
@click.option(
    '--update-rc-builds-cards', is_flag=True, help='Update cards in RC builds column with `target_ref` version'
)
@click.option(
    '--move-cards',
    is_flag=True,
    help='Do not create a card for a change, but move the existing card from '
    + '`HAVE BUGS - FIXME` or `FIXED - Ready to Rebuild` to INBOX team',
)
@click.pass_context
def testable(
    ctx: click.Context,
    base_ref: str,
    target_ref: str,
    milestone: str,
    dry_run: bool,
    update_rc_builds_cards: bool,
    move_cards: bool,
) -> None:
    """
    Create a Trello card for changes since a previous release (referenced by `BASE_REF`)
    that need to be tested for the next release (referenced by `TARGET_REF`).

    `BASE_REF` and `TARGET_REF` can be any valid git references. It practice, you should use either:

    * A tag: `7.16.1`, `7.17.0-rc.4`, ...

    * A release branch: `6.16.x`, `7.17.x`, ...

    * The `master` branch.

    NOTE: using a minor version shorthand (e.g. `7.16`) is not supported, as it is ambiguous.

    Example: assuming we are working on the release of 7.17.0, we can...

    * Create cards for changes between a previous Agent release and `master` (useful when preparing an initial RC):

        `$ ddev release trello testable 7.16.1 origin/master`

    * Create cards for changes between a previous RC and `master` (useful when preparing a new RC, and a separate
    release branch was not created yet):

        `$ ddev release trello testable 7.17.0-rc.2 origin/master`

    * Create cards for changes between a previous RC and a release branch (useful to only review changes in a
    release branch that has diverged from `master`):

        `$ ddev release trello testable 7.17.0-rc.4 7.17.x`

    * Create cards for changes between two arbitrary tags, e.g. between RCs:

        `$ ddev release trello testable 7.17.0-rc.4 7.17.0-rc.5`

    TIP: run with `ddev -x release trello testable` to force the use of the current directory.
    To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.


    See trello subcommand for details on how to setup access:

    `ddev release trello -h`.
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
        options = {
            '1': 'Integrations',
            '2': 'Infra-Integrations',
            '3': 'Containers',
            '4': 'Core',
            '5': 'Platform',
            '6': 'Tools and Libraries',
            's': 'Skip',
            'q': 'Quit',
        }
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
            '9': 'Infra-Integrations',
            '10': 'Tools and Libraries',
            's': 'Skip',
            'q': 'Quit',
        }
    default_option = get_next(options)
    options_prompt = f'Choose an option (default {options[default_option]}): '
    options_text = '\n' + '\n'.join('{} - {}'.format(key, value) for key, value in options.items())

    commit_ids: Set[str] = set()
    user_config = cast(Dict[Any, Any], ctx.obj)
    trello = TrelloClient(user_config)

    fixed_cards_mover = None
    if move_cards:
        fixed_cards_mover = FixedCardsMover(trello, dry_run)

    rc_build_cards_updater = None
    if update_rc_builds_cards:
        rc_build_cards_updater = RCBuildCardsUpdater(trello, target_ref)

    card_assignments: Dict[str, Dict[str, int]] = {}

    github_teams = trello.label_github_team_map.values()
    testerSelector = create_tester_selector(trello, repo, github_teams, user_config, APP_DIR)
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
        skip_qa = False
        for label in pr_labels:
            if label == "qa/skip-qa":
                skip_qa = True
            elif label.startswith('documentation'):
                documentation_pr = True
            elif label.startswith(CHANGELOG_LABEL_PREFIX) and label.split('/', 1)[1] != CHANGELOG_TYPE_NONE:
                nochangelog_pr = False

        if documentation_pr and nochangelog_pr:
            echo_info(f'Skipping documentation {format_commit_id(commit_id)}.')
            continue

        if skip_qa:
            echo_info(f'Skipping because of skip-qa label {format_commit_id(commit_id)}.')
            continue

        pr_milestone = get_pr_milestone(pr_data)
        if milestone and pr_milestone != milestone:
            echo_info(
                f'Looking for milestone {milestone}, skipping {format_commit_id(commit_id)}'
                + f' with milestone {pr_milestone}.'
            )
            continue

        pr_url = pr_data.get('html_url', f'https://github.com/DataDog/{repo}/pull/{commit_id}')
        pr_title = pr_data.get('title', commit_subject)
        pr_author = pr_data.get('user', {}).get('login', '')
        pr_body = pr_data.get('body', '')
        pr_num = pr_data.get('number', 0)

        trello_config = user_config['trello']
        if not (trello_config['key'] and trello_config['token']):
            abort('Error: You are not authenticated for Trello. Please set your trello ddev config')

        if fixed_cards_mover and fixed_cards_mover.try_move_card(pr_url):
            continue
        teams = [trello.label_team_map[label] for label in pr_labels if label in trello.label_team_map]
        if teams:
            create_trello_card(
                trello,
                testerSelector,
                teams,
                pr_num,
                pr_title,
                pr_url,
                pr_labels,
                pr_body,
                dry_run,
                pr_author,
                user_config,
                card_assignments,
            )
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
                create_trello_card(
                    trello,
                    testerSelector,
                    [value],
                    pr_num,
                    pr_title,
                    pr_url,
                    pr_labels,
                    pr_body,
                    dry_run,
                    pr_author,
                    user_config,
                    card_assignments,
                )

            finished = True
    if rc_build_cards_updater and not dry_run:
        rc_build_cards_updater.update_cards()

    if dry_run:
        show_card_assigments(testerSelector)


def show_card_assigments(testerSelector: TesterSelector):
    echo_info('Cards assignments')
    stat = testerSelector.get_stats()

    for team, v in stat.items():
        echo_info(team)
        for user, prs in v.items():
            prs_str = ", ".join([str(pr) for pr in prs])
            echo_info(f"\t- {user}: {prs_str}")
