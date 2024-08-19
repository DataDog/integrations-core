# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import call as c

import pytest

from ddev.utils.git import GitRepository

NO_CONFIRMATION_SO_ABORT = 'Did not get confirmation, aborting. Did not create or push the tag.'


@pytest.fixture
def basic_git(mocker):
    mock_git = mocker.create_autospec(GitRepository)
    # We're patching the constructor (__new__) method of GitRepository class.
    # That's why we need a function that returns the mock.
    mocker.patch('ddev.repo.core.GitRepository', lambda _: mock_git)
    return mock_git


@pytest.fixture
def git(basic_git):
    basic_git.current_branch.return_value = '7.56.x'
    basic_git.tags.return_value = [
        # interesting phenomena:
        # - skipping RCs
        # - rc 11 naively would be sorted as less than rc 2
        # - an rc tag from dbm
        # '7.56.0',
        '7.56.0-rc.1',
        '7.56.0-rc.1-dbm-agent-jobs',
        '7.56.0-rc.11',
        '7.56.0-rc.2',
        '7.56.0-rc.5',
        '7.56.0-rc.6',
        '7.56.0-rc.7',
        '7.56.0-rc.8',
    ]
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
    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [12]' in result.output


@pytest.mark.parametrize(
    'no_confirm',
    [
        pytest.param('n', id='explicit abort'),
        pytest.param('', id='abort by default'),
        pytest.param('x', id='abort on any other input'),
    ],
)
@pytest.mark.parametrize('rc_num', ['3', '10'])
def test_do_not_confirm_non_sequential_rc(ddev, git, rc_num, no_confirm):
    """
    We're in the middle of a release, some RCs are already done. User wants to create the next RC.

    However the user asks to create an RC that's less than the latest RC number.
    This is unusual, so we give a warning and ask user to confirm. If they don't, we abort.

    Important: we are not overwriting an existing RC tag.
    """

    result = ddev('release', 'branch', 'tag', input=f'{rc_num}\n{no_confirm}\n')

    assert result.exit_code == 1, result.output
    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [12]' in result.output
    assert (
        '!!! WARNING !!!\n'
        'You are about to create an RC with a number less than the latest RC number (12). Are you sure? [y/N]'
    ) in result.output
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

    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [12]' in result.output
    assert (
        '!!! WARNING !!!\n'
        'You are about to create an RC with a number less than the latest RC number (12). Are you sure? [y/N]'
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
    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [12]' in result.output
    assert (f'Tag 7.56.0-rc.{rc_num} already exists. Switch to git to overwrite it.') in result.output


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

    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [1]' in result.output
    assert result.exit_code == 1, result.output
    assert NO_CONFIRMATION_SO_ABORT in result.output


def test_first_rc(ddev, git):
    """
    First RC for a new release.
    add some more examples?
    should be ok to specify a number other than 1
    """
    git.tags.return_value = []

    result = ddev('release', 'branch', 'tag', input='\ny\n')

    _assert_tag_pushed(git, result, '7.56.0-rc.1')
    assert 'Which RC number are we tagging? (hit ENTER to accept suggestion) [1]' in result.output


def test_final(ddev, git):
    """
    Create final release tag.

    We should handle the case of bugfix releases here too
    """
    result = ddev('release', 'branch', 'tag', '--final', input='y\n')

    _assert_tag_pushed(git, result, '7.56.0')
