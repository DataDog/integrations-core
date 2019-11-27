# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from collections import OrderedDict, namedtuple
from datetime import datetime

import click
from semver import finalize_version, parse_version_info
from six import StringIO, iteritems

from ...subprocess import run_command
from ...utils import (
    basepath,
    chdir,
    dir_exists,
    ensure_unicode,
    get_next,
    remove_path,
    resolve_path,
    stream_file_lines,
    write_file,
)
from ..constants import (
    BETA_PACKAGES,
    CHANGELOG_LABEL_PREFIX,
    CHANGELOG_TYPE_NONE,
    NOT_CHECKS,
    VERSION_BUMP,
    get_agent_release_requirements,
    get_root,
)
from ..git import get_commits_since, get_current_branch, git_commit, git_tag
from ..github import (
    from_contributor,
    get_changelog_types,
    get_pr,
    get_pr_from_hash,
    get_pr_labels,
    get_pr_milestone,
    parse_pr_number,
    parse_pr_numbers,
)
from ..release import (
    build_package,
    get_agent_requirement_line,
    get_release_tag_string,
    update_agent_requirements,
    update_version_module,
)
from ..trello import TrelloClient
from ..utils import format_commit_id, get_bump_function, get_current_agent_version, get_valid_checks, get_version_string
from .console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning

ChangelogEntry = namedtuple('ChangelogEntry', 'number, title, url, author, author_url, from_contributor')


def validate_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    try:
        parts = value.split('.')
        if len(parts) == 2:
            parts.append('0')
        version_info = parse_version_info('.'.join(parts))
        return '{}.{}'.format(version_info.major, version_info.minor)
    except ValueError:
        raise click.BadParameter('needs to be in semver format x.y[.z]')


def create_trello_card(client, teams, pr_title, pr_url, pr_body, dry_run):
    body = u'Pull request: {}\n\n{}'.format(pr_url, pr_body)

    for team in teams:
        if dry_run:
            echo_success('Will create a card for team {}: '.format(team), nl=False)
            echo_info(pr_title)
            continue
        creation_attempts = 3
        for attempt in range(3):
            rate_limited, error, response = client.create_card(team, pr_title, body)
            if rate_limited:
                wait_time = 10
                echo_warning(
                    'Attempt {} of {}: A rate limit in effect, retrying in {} '
                    'seconds...'.format(attempt + 1, creation_attempts, wait_time)
                )
                time.sleep(wait_time)
            elif error:
                if attempt + 1 == creation_attempts:
                    echo_failure('Error: {}'.format(error))
                    break

                wait_time = 2
                echo_warning(
                    'Attempt {} of {}: An error has occurred, retrying in {} '
                    'seconds...'.format(attempt + 1, creation_attempts, wait_time)
                )
                time.sleep(wait_time)
            else:
                echo_success('Created card for team {}: '.format(team), nl=False)
                echo_info(response.json().get('url'))
                break


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage the release of checks')
def release():
    pass


@release.group(context_settings=CONTEXT_SETTINGS, short_help='Show release information')
def show():
    """To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.
    """
    pass


@show.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the checks that can be released')
@click.option('--quiet', '-q', is_flag=True)
@click.pass_context
def ready(ctx, quiet):
    """Show all the checks that can be released."""
    user_config = ctx.obj
    cached_prs = {}

    for target in sorted(get_valid_checks()):
        # get the name of the current release tag
        cur_version = get_version_string(target)
        target_tag = get_release_tag_string(target, cur_version)

        # get the diff from HEAD
        diff_lines = get_commits_since(target, target_tag)

        # get the number of PRs that could be potentially released
        # Only show the ones that have a changelog label that isn't no-changelog
        pr_numbers = parse_pr_numbers(diff_lines)

        shippable_prs = 0
        for pr_num in pr_numbers:
            try:
                if pr_num in cached_prs:
                    changelog_labels = cached_prs[pr_num]
                    if len(changelog_labels) != 1:
                        continue
                else:
                    payload = get_pr(pr_num, user_config)
                    changelog_labels = get_changelog_types(payload)
                    cached_prs[pr_num] = changelog_labels

                    if not changelog_labels:
                        echo_warning(
                            'PR #{} has no changelog label attached, please add one! Skipping...'.format(pr_num)
                        )
                        continue

                    if len(changelog_labels) > 1:
                        echo_warning(
                            'Multiple changelog labels found attached to PR #{}, '
                            'please only use one! Skipping...'.format(pr_num)
                        )
                        continue

                if changelog_labels[0] != CHANGELOG_TYPE_NONE:
                    shippable_prs += 1
            except Exception as e:
                echo_failure('Unable to fetch info for PR #{}: {}'.format(pr_num, e))
                continue

        if shippable_prs:
            if quiet:
                msg = target
            else:
                msg = 'Check {} has {} out of {} merged PRs that could be released' ''.format(
                    target, shippable_prs, len(pr_numbers)
                )
            echo_info(msg)


@show.command(context_settings=CONTEXT_SETTINGS, short_help='Show all the pending PRs for a given check')
@click.argument('check')
@click.option('--dry-run', '-n', is_flag=True)
@click.pass_context
def changes(ctx, check, dry_run):
    """Show all the pending PRs for a given check."""
    if not dry_run and check not in get_valid_checks():
        abort('Check `{}` is not an Agent-based Integration'.format(check))

    # get the name of the current release tag
    cur_version = get_version_string(check)
    target_tag = get_release_tag_string(check, cur_version)

    # get the diff from HEAD
    diff_lines = get_commits_since(check, target_tag)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    if not dry_run:
        echo_info('Found {} PRs merged since tag: {}'.format(len(pr_numbers), target_tag))

    user_config = ctx.obj
    if dry_run:
        changelog_types = []

        for pr_num in pr_numbers:
            try:
                payload = get_pr(pr_num, user_config)
            except Exception as e:
                echo_failure('Unable to fetch info for PR #{}: {}'.format(pr_num, e))
                continue

            current_changelog_types = get_changelog_types(payload)
            if not current_changelog_types:
                abort('No valid changelog labels found attached to PR #{}, please add one!'.format(pr_num))
            elif len(current_changelog_types) > 1:
                abort('Multiple changelog labels found attached to PR #{}, please only use one!'.format(pr_num))

            current_changelog_type = current_changelog_types[0]
            if current_changelog_type != 'no-changelog':
                changelog_types.append(current_changelog_type)

        return cur_version, changelog_types
    else:
        for pr_num in pr_numbers:
            try:
                payload = get_pr(pr_num, user_config)
            except Exception as e:
                echo_failure('Unable to fetch info for PR #{}: {}'.format(pr_num, e))
                continue

            changelog_types = get_changelog_types(payload)

            echo_success(payload.get('title'))
            echo_info(' * Url: {}'.format(payload.get('html_url')))

            echo_info(' * Changelog status: ', nl=False)
            if not changelog_types:
                echo_warning('WARNING! No changelog labels attached.\n')
            elif len(changelog_types) > 1:
                echo_warning('WARNING! Too many changelog labels attached: {}\n'.format(', '.join(changelog_types)))
            else:
                echo_success('{}\n'.format(changelog_types[0]))


@release.command(
    context_settings=CONTEXT_SETTINGS, short_help='Create a Trello card for each change that needs to be tested'
)
@click.option('--start', 'start_id', help='The PR number or commit hash to start at')
@click.option('--since', 'agent_version', callback=validate_version, help='The version of the Agent to compare')
@click.option('--milestone', help='The PR milestone to filter by')
@click.option('--dry-run', '-n', is_flag=True, help='Only show the changes')
@click.pass_context
def testable(ctx, start_id, agent_version, milestone, dry_run):
    """Create a Trello card for each change that needs to be tested for
    the next release. Run via `ddev -x release testable` to force the use
    of the current directory.

    To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

    \b
    To use Trello:
    1. Go to `https://trello.com/app-key` and copy your API key.
    2. Run `ddev config set trello.key` and paste your API key.
    3. Go to `https://trello.com/1/authorize?key=key&name=name&scope=read,write&expiration=never&response_type=token`,
       where `key` is your API key and `name` is the name to give your token, e.g. ReleaseTestingYourName.
       Authorize access and copy your token.
    4. Run `ddev config set trello.token` and paste your token.
    """
    root = get_root()
    repo = basepath(root)
    if repo not in ('integrations-core', 'datadog-agent'):
        abort('Repo `{}` is unsupported.'.format(repo))

    if agent_version:
        current_agent_version = agent_version
    else:
        echo_waiting('Finding the current minor release of the Agent... ', nl=False)
        current_agent_version = get_current_agent_version()
        echo_success(current_agent_version)

    current_release_branch = '{}.x'.format(current_agent_version)
    diff_target_branch = 'master'
    echo_info('Branch `{}` will be compared to `{}`.'.format(current_release_branch, diff_target_branch))

    echo_waiting('Getting diff... ', nl=False)
    diff_command = 'git --no-pager log "--pretty=format:%H %s" {}..{}'

    with chdir(root):
        fetch_command = 'git fetch --dry'
        result = run_command(fetch_command, capture=True)
        if result.code:
            abort('Unable to run {}.'.format(fetch_command))

        if current_release_branch in result.stderr or diff_target_branch in result.stderr:
            abort(
                'Your repository is not sync with the remote repository. Please run git fetch in {} folder.'.format(
                    root
                )
            )

        # compare with the local tag first
        reftag = '{}{}'.format('refs/tags/', current_release_branch)
        result = run_command(diff_command.format(reftag, diff_target_branch), capture=True)
        if result.code:
            # if it didn't work, compare with a branch.
            origin_release_branch = 'origin/{}'.format(current_release_branch)
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
        options = OrderedDict(
            (('1', 'Integrations'), ('2', 'Containers'), ('3', 'Core'), ('4', 'Platform'), ('s', 'Skip'), ('q', 'Quit'))
        )
    else:
        options = OrderedDict(
            (
                ('1', 'Core'),
                ('2', 'Containers'),
                ('3', 'Logs'),
                ('4', 'Platform'),
                ('5', 'Process'),
                ('6', 'Trace'),
                ('7', 'Integrations'),
                ('s', 'Skip'),
                ('q', 'Quit'),
            )
        )
    default_option = get_next(options)
    options_prompt = 'Choose an option (default {}): '.format(options[default_option])
    options_text = '\n' + '\n'.join('{} - {}'.format(key, value) for key, value in iteritems(options))

    commit_ids = set()
    user_config = ctx.obj
    trello = TrelloClient(user_config)
    found_start_id = False

    for i, (commit_hash, commit_subject) in enumerate(diff_data, 1):
        commit_id = parse_pr_number(commit_subject)
        if commit_id:
            api_response = get_pr(commit_id, user_config, repo=repo, raw=True)
            if api_response.status_code == 401:
                abort('Access denied. Please ensure your GitHub token has correct permissions.')
            elif api_response.status_code == 403:
                echo_failure(
                    'Error getting info for #{}. Please set a GitHub HTTPS '
                    'token to avoid rate limits.'.format(commit_id)
                )
                continue
            elif api_response.status_code == 404:
                echo_info('Skipping #{}, not a pull request...'.format(commit_id))
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
                        'token to avoid rate limits.'.format(commit_id)
                    )
                    continue

                api_response.raise_for_status()
                pr_data = api_response.json()
                pr_data = pr_data.get('items', [{}])[0]
            # Commit to master
            except IndexError:
                pr_data = {
                    'number': commit_hash,
                    'html_url': 'https://github.com/DataDog/{}/commit/{}'.format(repo, commit_hash),
                }
            commit_id = str(pr_data.get('number', ''))

        if commit_id and commit_id in commit_ids:
            echo_info('Already seen PR #{}, skipping it.'.format(commit_id))
            continue
        commit_ids.add(commit_id)

        if start_id and not found_start_id:
            if start_id == commit_id or start_id == commit_hash:
                found_start_id = True
            else:
                echo_info(
                    'Looking for {}, skipping {}.'.format(format_commit_id(start_id), format_commit_id(commit_id))
                )
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
            echo_info('Skipping documentation {}.'.format(format_commit_id(commit_id)))
            continue

        pr_milestone = get_pr_milestone(pr_data)
        if milestone and pr_milestone != milestone:
            echo_info('Looking for milestone {}, skipping {}.'.format(milestone, format_commit_id(commit_id)))
            continue

        pr_url = pr_data.get('html_url', 'https://github.com/DataDog/{}/pull/{}'.format(repo, commit_id))
        pr_title = pr_data.get('title', commit_subject)
        pr_author = pr_data.get('user', {}).get('login', '')
        pr_body = pr_data.get('body', '')

        teams = [trello.label_team_map[label] for label in pr_labels if label in trello.label_team_map]
        if teams:
            create_trello_card(trello, teams, pr_title, pr_url, pr_body, dry_run)
            continue

        finished = False
        choice_error = ''
        progress_status = '({} of {}) '.format(i, num_changes)
        indent = ' ' * len(progress_status)

        while not finished:
            echo_success('\n{}{}'.format(progress_status, pr_title))

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
                try:
                    choice = ensure_unicode(choice)
                except UnicodeDecodeError:
                    choice = repr(choice)

            if not choice:
                choice = default_option

            if choice not in options:
                echo_info(choice)
                choice_error = u'`{}` is not a valid option.'.format(choice)
                continue
            else:
                choice_error = ''

            value = options[choice]
            echo_info(value)

            if value == 'Skip':
                echo_info('Skipped {}'.format(format_commit_id(commit_id)))
                break
            elif value == 'Quit':
                echo_warning('Exited at {}'.format(format_commit_id(commit_id)))
                return
            else:
                create_trello_card(trello, [value], pr_title, pr_url, pr_body, dry_run)

            finished = True


@release.command(context_settings=CONTEXT_SETTINGS, short_help='Tag the git repo with the current release of a check')
@click.argument('check')
@click.argument('version', required=False)
@click.option('--push/--no-push', default=True)
@click.option('--dry-run', '-n', is_flag=True)
def tag(check, version, push, dry_run):
    """Tag the HEAD of the git repo with the current release number for a
    specific check. The tag is pushed to origin by default.

    You can tag everything at once by setting the check to `all`.

    Notice: specifying a different version than the one in __about__.py is
    a maintenance task that should be run under very specific circumstances
    (e.g. re-align an old release performed on the wrong commit).
    """
    tagging_all = check == 'all'

    valid_checks = get_valid_checks()
    if not tagging_all and check not in valid_checks:
        abort('Check `{}` is not an Agent-based Integration'.format(check))

    if tagging_all:
        if version:
            abort('You cannot tag every check with the same version')
        checks = sorted(valid_checks)
    else:
        checks = [check]

    # Check for any new tags
    tagged = False

    for check in checks:
        echo_info('{}:'.format(check))

        # get the current version
        if not version:
            version = get_version_string(check)

        # get the tag name
        release_tag = get_release_tag_string(check, version)
        echo_waiting('Tagging HEAD with {}... '.format(release_tag), indent=True, nl=False)

        if dry_run:
            version = None
            click.echo()
            continue

        result = git_tag(release_tag, push)

        if result.code == 128 or 'already exists' in result.stderr:
            echo_warning('already exists')
        elif result.code != 0:
            abort('\n{}{}'.format(result.stdout, result.stderr), code=result.code)
        else:
            tagged = True
            echo_success('success!')

        # Reset version
        version = None

    if not tagged:
        abort(code=2)


@release.command(context_settings=CONTEXT_SETTINGS, short_help='Release one or more checks')
@click.argument('checks', nargs=-1, required=True)
@click.option('--version')
@click.option('--new', 'initial_release', is_flag=True, help='Ensure versions are at 1.0.0')
@click.option('--skip-sign', is_flag=True, help='Skip the signing of release metadata')
@click.option('--sign-only', is_flag=True, help='Only sign release metadata')
@click.pass_context
def make(ctx, checks, version, initial_release, skip_sign, sign_only):
    """Perform a set of operations needed to release checks:

    \b
      * update the version in __about__.py
      * update the changelog
      * update the requirements-agent-release.txt file
      * update in-toto metadata
      * commit the above changes

    You can release everything at once by setting the check to `all`.

    \b
    If you run into issues signing:
    \b
      - Ensure you did `gpg --import <YOUR_KEY_ID>.gpg.pub`
    """
    # Import lazily since in-toto runs a subprocess to check for gpg2 on load
    from ..signing import update_link_metadata, YubikeyException

    releasing_all = 'all' in checks

    valid_checks = get_valid_checks()
    if not releasing_all:
        for check in checks:
            if check not in valid_checks:
                abort('Check `{}` is not an Agent-based Integration'.format(check))

    # don't run the task on the master branch
    if get_current_branch() == 'master':
        abort('Please create a release branch, you do not want to commit to master directly.')

    if releasing_all:
        if version:
            abort('You cannot bump every check to the same version')
        checks = sorted(valid_checks)
    else:
        checks = sorted(checks)

    if initial_release:
        version = '1.0.0'

    # Keep track of the list of checks that have been updated.
    updated_checks = []
    for check in checks:
        if sign_only:
            updated_checks.append(check)
            continue
        elif initial_release and check in BETA_PACKAGES:
            continue

        # Initial releases will only bump if not already 1.0.0 so no need to always output
        if not initial_release:
            echo_success('Check `{}`'.format(check))

        if version:
            # sanity check on the version provided
            cur_version = get_version_string(check)

            if version == 'final':
                # Remove any pre-release metadata
                version = finalize_version(cur_version)
            else:
                # Keep track of intermediate version bumps
                prev_version = cur_version
                for method in version.split(','):
                    # Apply any supported version bumping methods. Chaining is required for going
                    # from mainline releases to development releases since e.g. x.y.z > x.y.z-rc.A.
                    # So for an initial bug fix dev release you can do `fix,rc`.
                    if method in VERSION_BUMP:
                        version = VERSION_BUMP[method](prev_version)
                        prev_version = version

            p_version = parse_version_info(version)
            p_current = parse_version_info(cur_version)
            if p_version <= p_current:
                if initial_release:
                    continue
                else:
                    abort('Current version is {}, cannot bump to {}'.format(cur_version, version))
        else:
            cur_version, changelog_types = ctx.invoke(changes, check=check, dry_run=True)
            if not changelog_types:
                echo_warning('No changes for {}, skipping...'.format(check))
                continue
            bump_function = get_bump_function(changelog_types)
            version = bump_function(cur_version)

        if initial_release:
            echo_success('Check `{}`'.format(check))

        # update the version number
        echo_info('Current version of check {}: {}'.format(check, cur_version))
        echo_waiting('Bumping to {}... '.format(version), nl=False)
        update_version_module(check, cur_version, version)
        echo_success('success!')

        # update the CHANGELOG
        echo_waiting('Updating the changelog... ', nl=False)
        # TODO: Avoid double GitHub API calls when bumping all checks at once
        ctx.invoke(
            changelog,
            check=check,
            version=version,
            old_version=cur_version,
            initial=initial_release,
            quiet=True,
            dry_run=False,
        )
        echo_success('success!')

        commit_targets = [check]
        updated_checks.append(check)
        # update the list of integrations to be shipped with the Agent
        if check not in NOT_CHECKS:
            req_file = get_agent_release_requirements()
            commit_targets.append(os.path.basename(req_file))
            echo_waiting('Updating the Agent requirements file... ', nl=False)
            update_agent_requirements(req_file, check, get_agent_requirement_line(check, version))
            echo_success('success!')

        echo_waiting('Committing files...')

        # commit the changes.
        # do not use [ci skip] so releases get built https://docs.gitlab.com/ee/ci/yaml/#skipping-jobs
        msg = '[Release] Bumped {} version to {}'.format(check, version)
        git_commit(commit_targets, msg)

        if not initial_release:
            # Reset version
            version = None

    if sign_only or not skip_sign:
        if not updated_checks:
            abort('There are no new checks to sign and release!')
        echo_waiting('Updating release metadata...')
        echo_info('Please touch your Yubikey immediately after entering your PIN!')
        try:
            commit_targets = update_link_metadata(updated_checks)
            git_commit(commit_targets, '[Release] Update metadata', force=True)
        except YubikeyException as e:
            abort('A problem occurred while signing metadata: {}'.format(e))

    # done
    echo_success('All done, remember to push to origin and open a PR to merge these changes on master')


@release.command(context_settings=CONTEXT_SETTINGS, short_help='Update the changelog for a check')
@click.argument('check')
@click.argument('version')
@click.argument('old_version', required=False)
@click.option('--initial', is_flag=True)
@click.option('--quiet', '-q', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.pass_context
def changelog(ctx, check, version, old_version, initial, quiet, dry_run):
    """Perform the operations needed to update the changelog.

    This method is supposed to be used by other tasks and not directly.
    """
    if check not in get_valid_checks():
        abort('Check `{}` is not an Agent-based Integration'.format(check))

    # sanity check on the version provided
    cur_version = old_version or get_version_string(check)
    if parse_version_info(version) <= parse_version_info(cur_version):
        abort('Current version is {}, cannot bump to {}'.format(cur_version, version))

    if not quiet:
        echo_info('Current version of check {}: {}, bumping to: {}'.format(check, cur_version, version))

    # get the name of the current release tag
    target_tag = get_release_tag_string(check, cur_version)

    # get the diff from HEAD
    diff_lines = get_commits_since(check, None if initial else target_tag)

    # for each PR get the title, we'll use it to populate the changelog
    pr_numbers = parse_pr_numbers(diff_lines)
    if not quiet:
        echo_info('Found {} PRs merged since tag: {}'.format(len(pr_numbers), target_tag))

    if initial:
        # Only use the first one
        del pr_numbers[:-1]

    user_config = ctx.obj
    entries = []
    for pr_num in pr_numbers:
        try:
            payload = get_pr(pr_num, user_config)
        except Exception as e:
            echo_failure('Unable to fetch info for PR #{}: {}'.format(pr_num, e))
            continue

        changelog_labels = get_changelog_types(payload)

        if not changelog_labels:
            abort('No valid changelog labels found attached to PR #{}, please add one!'.format(pr_num))
        elif len(changelog_labels) > 1:
            abort('Multiple changelog labels found attached to PR #{}, please only use one!'.format(pr_num))

        changelog_type = changelog_labels[0]
        if changelog_type == CHANGELOG_TYPE_NONE:
            if not quiet:
                # No changelog entry for this PR
                echo_info('Skipping PR #{} from changelog due to label'.format(pr_num))
            continue

        author = payload.get('user', {}).get('login')
        author_url = payload.get('user', {}).get('html_url')
        title = '[{}] {}'.format(changelog_type, payload.get('title'))

        entry = ChangelogEntry(pr_num, title, payload.get('html_url'), author, author_url, from_contributor(payload))

        entries.append(entry)

    # store the new changelog in memory
    new_entry = StringIO()

    # the header contains version and date
    header = '## {} / {}\n'.format(version, datetime.utcnow().strftime('%Y-%m-%d'))
    new_entry.write(header)

    # one bullet point for each PR
    new_entry.write('\n')
    for entry in entries:
        thanks_note = ''
        if entry.from_contributor:
            thanks_note = ' Thanks [{}]({}).'.format(entry.author, entry.author_url)
        new_entry.write('* {}. See [#{}]({}).{}\n'.format(entry.title, entry.number, entry.url, thanks_note))
    new_entry.write('\n')

    # read the old contents
    changelog_path = os.path.join(get_root(), check, 'CHANGELOG.md')
    old = list(stream_file_lines(changelog_path))

    # write the new changelog in memory
    changelog_buffer = StringIO()

    # preserve the title
    changelog_buffer.write(''.join(old[:2]))

    # prepend the new changelog to the old contents
    # make the command idempotent
    if header not in old:
        changelog_buffer.write(new_entry.getvalue())

    # append the rest of the old changelog
    changelog_buffer.write(''.join(old[2:]))

    # print on the standard out in case of a dry run
    if dry_run:
        echo_info(changelog_buffer.getvalue())
    else:
        # overwrite the old changelog
        write_file(changelog_path, changelog_buffer.getvalue())


@release.command(context_settings=CONTEXT_SETTINGS, short_help='Build a wheel for a check')
@click.argument('check')
@click.option('--sdist', '-s', is_flag=True)
def build(check, sdist):
    """Build a wheel for a check as it is on the repo HEAD"""
    if check in get_valid_checks():
        check_dir = os.path.join(get_root(), check)
    else:
        check_dir = resolve_path(check)
        if not dir_exists(check_dir):
            abort('`{}` is not an Agent-based Integration or Python package'.format(check))

        check = basepath(check_dir)

    echo_waiting('Building `{}`...'.format(check))

    dist_dir = os.path.join(check_dir, 'dist')
    remove_path(dist_dir)

    result = build_package(check_dir, sdist)
    if result.code != 0:
        abort(result.stdout, result.code)

    echo_info('Build done, artifact(s) in: {}'.format(dist_dir))
    echo_success('Success!')


@release.command(context_settings=CONTEXT_SETTINGS, short_help='Build and upload a check to PyPI')
@click.argument('check')
@click.option('--sdist', '-s', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.pass_context
def upload(ctx, check, sdist, dry_run):
    """Release a specific check to PyPI as it is on the repo HEAD."""
    if check in get_valid_checks():
        check_dir = os.path.join(get_root(), check)
    else:
        check_dir = resolve_path(check)
        if not dir_exists(check_dir):
            abort('`{}` is not an Agent-based Integration or Python package'.format(check))

        check = basepath(check_dir)

    # retrieve credentials
    pypi_config = ctx.obj.get('pypi', {})
    username = pypi_config.get('user') or os.getenv('TWINE_USERNAME')
    password = pypi_config.get('pass') or os.getenv('TWINE_PASSWORD')
    if not (username and password):
        abort('This requires pypi.user and pypi.pass configuration. Please see `ddev config -h`.')

    auth_env_vars = {'TWINE_USERNAME': username, 'TWINE_PASSWORD': password}
    echo_waiting('Building and publishing `{}` to PyPI...'.format(check))

    with chdir(check_dir, env_vars=auth_env_vars):
        result = build_package(check_dir, sdist)
        if result.code != 0:
            abort(result.stdout, result.code)
        echo_waiting('Uploading the package...')
        if not dry_run:
            result = run_command('twine upload --skip-existing dist{}*'.format(os.path.sep))
            if result.code != 0:
                abort(code=result.code)

    echo_success('Success!')
