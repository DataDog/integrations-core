# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import call as c

import pytest

from ddev.utils.git import GitRepository

NO_CONFIRMATION_SO_ABORT = 'Did not get confirmation, aborting. Did not create or push the tag.'
RC_NUMBER_PROMPT = 'What RC number are we tagging? (hit ENTER to accept suggestion) [{}]'

EXAMPLE_TAGS = [
    '7.56.0-rc.1',
    # Random RC tag from DBM. We should make sure we ignore it.
    '7.56.0-rc.1-dbm-agent-jobs',
    # Icluding RC 11 is interesting because it makes sure we we parse the versions before we sort them.
    # The naive sort will think RC 11 is earlier than RC 2.
    '7.56.0-rc.11',
    '7.56.0-rc.2',
    # Skipping RCs, we go from 2 to 5.
    '7.56.0-rc.5',
    '7.56.0-rc.6',
    '7.56.0-rc.7',
    '7.56.0-rc.8',
]


@pytest.fixture
def basic_git(mocker):
    mock_git = mocker.create_autospec(GitRepository)
    # We're patching the creation of the GitRepository class.
    # That's why we need a function that returns the mock.
    mocker.patch('ddev.repo.core.GitRepository', lambda _: mock_git)
    return mock_git


@pytest.fixture
def git(basic_git):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = EXAMPLE_TAGS[:]
    yield basic_git
    assert basic_git.method_calls[:4] == [
        c.current_branch(),
        c.pull('7.56.x'),
        c.fetch_tags(),
        c.tags(glob_pattern='7.56.*'),
    ]


def _assert_tag_pushed(git, result, tag):
    assert result.exit_code == 0, result.output
    assert git.method_calls[-2:] == [
        c.tag(tag, message=tag),
        c.push(tag),
    ]
    assert f'Create and push this tag: {tag}?' in result.output


def test_wrong_branch(ddev, basic_git):
    """
    Given a branch that doesn't match the release branch pattern we should abort.
    """
    name = 'foo'
    basic_git.current_branch.return_value = name

    result = ddev('release', 'branch', 'tag')

    assert result.exit_code == 1, result.output
    assert rf'Invalid branch name: {name}. Branch name must match the pattern ^\d+\.\d+\.x$' in result.output
    assert basic_git.method_calls == [c.current_branch()]


def test_middle_of_release_next_rc(ddev, git):
    """
    We're in the middle of a release, some RCs are already done. We want to create the next RC.
    """
    result = ddev('release', 'branch', 'tag', input='\ny\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.12')
    assert RC_NUMBER_PROMPT.format('12') in result.output


@pytest.mark.parametrize(
    'no_confirm',
    [
        pytest.param('n', id='explicit abort'),
        pytest.param('', id='abort by default'),
        pytest.param('x', id='abort on any other input'),
    ],
)
@pytest.mark.parametrize('rc_num', ['3', '10'])
@pytest.mark.parametrize('last_rc', [11, 12])
def test_do_not_confirm_non_sequential_rc(ddev, git, rc_num, no_confirm, last_rc):
    """
    We're in the middle of a release, some RCs are already done. User wants to create the next RC.

    However the user asks to create an RC that's less than the latest RC number.
    This is unusual, so we give a warning and ask user to confirm. If they don't, we abort.

    Important: we are not overwriting an existing RC tag.
    """

    git.tags.return_value.append(f'7.56.0-rc.{last_rc}')
    result = ddev('release', 'branch', 'tag', input=f'{rc_num}\n{no_confirm}\n')

    assert RC_NUMBER_PROMPT.format(str(last_rc + 1)) in result.output
    assert (
        '!!! WARNING !!!\n'
        f'The latest RC is {last_rc}. You are about to go back in time by creating an RC with a number less than that. '
        'Are you sure? [y/N]'
    ) in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


@pytest.mark.parametrize('rc_num', ['3', '10'])
def test_confirm_non_sequential_rc(ddev, git, rc_num):
    """
    We're in the middle of a release, some RCs are already done. User wants to create the next RC.

    However the user asks to create an RC that's less than the latest RC number.
    This is unusual, so we give a warning and ask user to confirm. If they do, we create the tag.

    Important: we are not overwriting an existing RC tag.
    """
    result = ddev('release', 'branch', 'tag', input=f'{rc_num}\ny\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert (
        '!!! WARNING !!!\n'
        'The latest RC is 11. You are about to go back in time by creating an RC with a number less than that. '
        'Are you sure? [y/N]'
    ) in result.output
    _assert_tag_pushed(git, result, f'7.56.0-rc.{rc_num}')


@pytest.mark.parametrize('rc_num', ['1', '5', '11'])
def test_abort_if_rc_tag_exists(ddev, git, rc_num):
    """
    We're in the middle of a release, some RCs are already done. User wants to create the next RC.

    However the user asks to create an RC for which we already have a tag. This requires special git flags to clobber
    the local and remote tags. To keep our logic simple we give up here and leave a hint how the user can proceed.
    """

    result = ddev('release', 'branch', 'tag', input=f'{rc_num}\ny\n')

    assert result.exit_code == 1, result.output
    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert f'Tag 7.56.0-rc.{rc_num} already exists. Switch to git to overwrite it.' in result.output


def test_abort_if_tag_less_than_one(ddev, git):
    """
    RC numbers less than 1 don't make any sense, so we abort if we get one.
    """
    result = ddev('release', 'branch', 'tag', input='0\ny\n')

    assert RC_NUMBER_PROMPT.format('12') in result.output
    assert result.exit_code == 1, result.output
    assert 'RC number must be at least 1.' in result.output


@pytest.mark.parametrize(
    'no_confirm',
    [
        pytest.param('n', id='explicit abort'),
        pytest.param('', id='abort by default'),
        pytest.param('x', id='abort on any other input'),
    ],
)
def test_abort_valid_rc(ddev, git, no_confirm):
    """
    The RC is fine but we don't confirm in the end, so we abort.
    """
    git.tags.return_value = []

    result = ddev('release', 'branch', 'tag', input='\n{no_confirm}\n')

    assert RC_NUMBER_PROMPT.format('1') in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


@pytest.mark.parametrize(
    'rc_num_input, rc_num',
    [
        pytest.param('', '1', id='implicit sequential'),
        pytest.param('', '1', id='explicit sequential'),
        pytest.param('2', '2', id='explicit non-sequential'),
    ],
)
@pytest.mark.parametrize('tags, patch', [([], '0'), (EXAMPLE_TAGS + ['7.56.0'], '1')])
def test_first_rc(ddev, git, rc_num_input, rc_num, tags, patch):
    """
    First RC for a new release.

    We support starting with a number other than 1, though that's very unlikely to happen in practice.
    """
    git.tags.return_value = tags

    result = ddev('release', 'branch', 'tag', input=f'{rc_num_input}\ny\n')

    _assert_tag_pushed(git, result, f'7.56.{patch}-rc.{rc_num}')
    assert RC_NUMBER_PROMPT.format('1') in result.output


@pytest.mark.parametrize(
    'latest_final_tag, expected_new_final_tag',
    [
        pytest.param('', '7.56.0', id='no final tag yet'),
        pytest.param('7.56.0', '7.56.1', id='final tag present, so we are making a bugfix release'),
    ],
)
def test_final(ddev, git, latest_final_tag, expected_new_final_tag):
    """
    Create final release tag.
    """
    git.tags.return_value.append(latest_final_tag)
    result = ddev('release', 'branch', 'tag', '--final', input='y\n')

    _assert_tag_pushed(git, result, expected_new_final_tag)


# TODO: test for adding RCs for a bugfix release
