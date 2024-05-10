# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil
from functools import partial

import pytest

from ddev.repo.core import Repository


class TestFix:
    def test_existing_pr(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_existing_pr.yaml')
        mocker.patch('ddev.utils.git.GitManager.capture', return_value='cfd8020b628cc24eebadae2ab79a3a1be285885c\nfoo')

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Add changelog enforcement

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )

        result = ddev('release', 'changelog', 'fix')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Fixed 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Add changelog enforcement ([#15459](https://github.com/DataDog/integrations-core/pull/15459))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_pr_no_changelog_required(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_pr_no_changelog_required.yaml')
        mocker.patch('ddev.utils.git.GitManager.capture', return_value='ed4909414c5aedeba347b523b3c40ecd651896ab\nfoo')

        expected = helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )
        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(expected)

        result = ddev('release', 'changelog', 'fix')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            No changelog entries required (changelog/no-changelog label found)
            """
        )

        assert changelog.read_text() == expected

    def test_no_pr(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nfoo',
                helpers.dedent(
                    """
                    diff --git a/ddev/CHANGELOG.md b/ddev/CHANGELOG.md
                    index 4bfffc346413..5603965b33ac 100644
                    --- a/ddev/CHANGELOG.md
                    +++ b/ddev/CHANGELOG.md
                    @@ -2,6 +2,10 @@

                    ## Unreleased

                    +***Added***:
                    +
                    +* Add changelog enforcement
                    +
                    ## 3.3.0 / 2023-07-20

                    ***Added***:
                    diff --git a/ddev/pyproject.toml b/ddev/pyproject.toml
                    index a2d9e8b863..4d93f38bbd 100644
                    --- a/ddev/pyproject.toml
                    +++ b/ddev/pyproject.toml
                    @@ -111,3 +111,6 @@ ban-relative-imports = "all"
                     [tool.ruff.per-file-ignores]
                     #Tests can use assertions and relative imports
                     "**/tests/**/*" = ["I252"]
                    +
                    +
                    +
                    """
                ),
            ],
        )

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Add changelog enforcement

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )

        result = ddev('release', 'changelog', 'fix')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Fixed 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Add changelog enforcement ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )


@pytest.fixture
def repo_with_towncrier(repository, helpers):
    (repository.path / 'towncrier.toml').write_text(
        helpers.dedent(
            r'''
            [tool.towncrier]
            # If you change the values for directory or filename, make sure to look for them in the code as well.
            directory = "changelog.d"
            filename = "CHANGELOG.md"
            start_string = "<!-- towncrier release notes start -->\n"
            underlines = ["", "", ""]
            template = "changelog_template.jinja"
            title_format = "## {version} / {project_date}"
            # We automatically link to PRs, but towncrier only has an issue template so we abuse that.
            issue_format = "([#{issue}](https://github.com/DataDog/integrations-core/pull/{issue}))"

            # The order of entries matters! It controls the order in which changelog sections are displayed.
            # https://towncrier.readthedocs.io/en/stable/configuration.html#use-a-toml-array-defined-order
            [[tool.towncrier.type]]
            directory="removed"
            name = "Removed"
            showcontent = true

            [[tool.towncrier.type]]
            directory="changed"
            name = "Changed"
            showcontent = true

            [[tool.towncrier.type]]
            directory="security"
            name = "Security"
            showcontent = true

            [[tool.towncrier.type]]
            directory="deprecated"
            name = "Deprecated"
            showcontent = true

            [[tool.towncrier.type]]
            directory="added"
            name = "Added"
            showcontent = true

            [[tool.towncrier.type]]
            directory="fixed"
            name = "Fixed"
            showcontent = true
            '''
        )
    )
    (repository.path / 'changelog_template.jinja').write_text(
        helpers.dedent(
            '''
            {% if sections[""] %}
            {% for category, val in definitions.items() if category in sections[""] %}
            ***{{ definitions[category]['name'] }}***:

            {% for text, values in sections[""][category].items() %}
            * {{ text }} {{ values|join(', ') }}
            {% endfor %}

            {% endfor %}
            {% else %}
            No significant changes.


            {% endif %}
            '''
        )
    )
    return repository


class TestNew:
    @pytest.fixture
    def fragments_dir(self, repo_with_towncrier, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')
        repo = Repository(repo_with_towncrier.path.name, str(repo_with_towncrier.path))
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                'M ddev/pyproject.toml',
                '',
                '',
                '0000000000000000000000000000000000000000\nFoo',
            ],
        )
        return repo_with_towncrier.path / 'ddev' / 'changelog.d'

    def test_start(self, ddev, fragments_dir, helpers, mocker):
        mocker.patch('click.edit', return_value=None)
        fragment_file = fragments_dir / '15476.added'

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            f'''
            Created news fragment at {fragment_file}
            Added 1 changelog entry
            '''
        )
        assert fragment_file.read_text() == "Foo"

    def test_explicit_message(self, ddev, fragments_dir, helpers, mocker):
        mocker.patch('click.edit', return_value=None)
        fragment_file = fragments_dir / '15476.added'

        result = ddev('release', 'changelog', 'new', 'added', '-m', 'Bar')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            f'''
            Created news fragment at {fragment_file}
            Added 1 changelog entry
            '''
        )
        assert fragment_file.read_text() == "Bar"

    def test_prompt_for_entry_type(self, ddev, fragments_dir, helpers, mocker):
        mocker.patch('click.edit', return_value=None)
        fragment_file = fragments_dir / '15476.added'

        result = ddev('release', 'changelog', 'new', input='added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            f'''
            Entry type? (removed, changed, security, deprecated, added, fixed): added
            Created news fragment at {fragment_file}
            Added 1 changelog entry
            '''
        )
        assert fragment_file.read_text() == "Foo"

    def test_start_no_changelog(self, ddev, fragments_dir, helpers, mocker):
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                'M tests/conftest.py',
                '',
                '',
                '0000000000000000000000000000000000000000\nFoo',
            ],
        )
        edit_patch = mocker.patch('click.edit', return_value=None)
        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            '''
            No changelog entries to create
            '''
        )
        assert not (fragments_dir / '15476.added').exists()
        edit_patch.assert_not_called()

    def test_edit_entry(self, ddev, fragments_dir, helpers, mocker):
        message = 'Foo \n\n    Bar'
        mocker.patch(
            'click.edit',
            return_value=message,
        )
        fragment_file = fragments_dir / '15476.added'

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            f'''
            Created news fragment at {fragment_file}
            Added 1 changelog entry
            '''
        )
        assert fragment_file.read_text() == message


class TestBuild:
    @pytest.fixture
    def build_changelog(self, repo_with_towncrier):
        '''
        We explicitly import and setup the command that only generates the changelog.

        This is needed because the "release make" command does too much.
        '''
        from click.testing import CliRunner
        from datadog_checks.dev.tooling.commands.release.changelog import changelog
        from datadog_checks.dev.tooling.constants import set_root

        set_root(repo_with_towncrier.path)

        return partial(CliRunner().invoke, changelog, catch_exceptions=False)

    @pytest.fixture
    def setup_changelog_build(self, repo_with_towncrier, helpers):
        changelog = repo_with_towncrier.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                '''
                # CHANGELOG - ddev

                <!-- towncrier release notes start -->

                ## 3.3.0 / 2023-07-20

                ***Added***:
                '''
            )
        )
        fragments_dir = repo_with_towncrier.path / 'ddev' / 'changelog.d'
        if fragments_dir.exists():
            shutil.rmtree(fragments_dir)
        fragments_dir.mkdir(parents=True)
        return changelog, fragments_dir

    def test_build(self, setup_changelog_build, helpers, build_changelog):
        '''
        This example checks several properties of a successful changelog:

        - Entries of the same entry type should be sorted.
        - Entry types should be sorted.
        - Multiline entries should preserve what user entered
        '''
        changelog, fragments_dir = setup_changelog_build
        (fragments_dir / '1.added').write_text("Foo")
        (fragments_dir / '2.fixed').write_text("Bar")
        (fragments_dir / '3.added').write_text('Foo\n\n    Bar')

        result = build_changelog(args=["ddev", "3.4.0", "--date", "2023-10-11"])

        assert result.exit_code == 0, result.output
        assert changelog.read_text() == helpers.dedent(
            '''
            # CHANGELOG - ddev

            <!-- towncrier release notes start -->

            ## 3.4.0 / 2023-10-11

            ***Added***:

            * Foo ([#1](https://github.com/DataDog/integrations-core/pull/1))
            * Foo

                  Bar ([#3](https://github.com/DataDog/integrations-core/pull/3))

            ***Fixed***:

            * Bar ([#2](https://github.com/DataDog/integrations-core/pull/2))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            '''
        )

    def test_build_dry_run(self, setup_changelog_build, helpers, build_changelog):
        changelog, fragments_dir = setup_changelog_build

        (fragments_dir / '1.added').write_text("Foo")

        result = build_changelog(args=["ddev", "3.4.0", "--date", "2023-10-11", "--dry-run"])

        assert result.exit_code == 0, result.output
        # The new changelog entry should appear in command output.
        assert (
            helpers.dedent(
                '''
                ## 3.4.0 / 2023-10-11

                ***Added***:

                * Foo ([#1](https://github.com/DataDog/integrations-core/pull/1))
                '''
            )
            in helpers.remove_trailing_spaces(result.output)
        )
        # Make sure that we don't write anything to the changelog.
        assert changelog.read_text() == helpers.dedent(
            '''
            # CHANGELOG - ddev

            <!-- towncrier release notes start -->

            ## 3.3.0 / 2023-07-20

            ***Added***:
            '''
        )
