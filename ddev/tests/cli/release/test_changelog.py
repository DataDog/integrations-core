# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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


class TestNew:
    def test_start(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_append(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Over (#9000)
            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_before(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', 'changed')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Changed***:

            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ***Added***:

            * Over (#9000)

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_after(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', 'fixed')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Over (#9000)

            ***Fixed***:

            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_multiple(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog1 = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog1.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        changelog2 = repository.path / 'postgres' / 'CHANGELOG.md'
        changelog2.write_text(
            helpers.dedent(
                """
                # CHANGELOG - postgres

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml\nM postgres/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 2 changelog entries
            """
        )

        assert changelog1.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Over (#9000)
            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )
        assert changelog2.read_text() == helpers.dedent(
            """
            # CHANGELOG - postgres

            ## Unreleased

            ***Added***:

            * Over (#9000)
            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_explicit_message(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )

        result = ddev('release', 'changelog', 'new', 'added', '-m', 'Bar')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Bar ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_prompt_for_entry_type(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ***Added***:

                * Over (#9000)

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch('click.edit', return_value=None)

        result = ddev('release', 'changelog', 'new', input='added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Entry type? (Removed, Changed, Security, Deprecated, Added, Fixed): added
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Over (#9000)
            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )

    def test_edit_entry(self, ddev, repository, helpers, network_replay, mocker):
        network_replay('release/changelog/fix_no_pr.yaml')

        repo = Repository(repository.path.name, str(repository.path))

        changelog = repository.path / 'ddev' / 'CHANGELOG.md'
        changelog.write_text(
            helpers.dedent(
                """
                # CHANGELOG - ddev

                ## Unreleased

                ## 3.3.0 / 2023-07-20

                ***Added***:
                """
            )
        )
        repo.git.capture('add', '.')
        repo.git.capture('commit', '-m', 'test')
        mocker.patch(
            'ddev.utils.git.GitManager.capture',
            side_effect=[
                '0000000000000000000000000000000000000000\nFoo',
                'M ddev/pyproject.toml',
                '',
                '',
            ],
        )
        mocker.patch(
            'click.edit',
            return_value='* Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))\n\n    Bar',
        )

        result = ddev('release', 'changelog', 'new', 'added')

        assert result.exit_code == 0, result.output
        assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
            """
            Added 1 changelog entry
            """
        )

        assert changelog.read_text() == helpers.dedent(
            """
            # CHANGELOG - ddev

            ## Unreleased

            ***Added***:

            * Foo ([#15476](https://github.com/DataDog/integrations-core/pull/15476))

                Bar

            ## 3.3.0 / 2023-07-20

            ***Added***:
            """
        )
