# Pull requests

## Separation of concerns

  Every pull request should do one thing only for easier Git management. For example, if you are
    editing documentation and notice an error in the shipped example configuration, fix the
    error in a separate pull request. Doing so enables a clean cherry-pick or revert of the bug fix
    should the need arise.

## Merges

  Datadog only allows GitHub's [squash and merge][github-squash-and-merge] to keep a clean Git history.

## Changelog entries

Different guidelines apply depending on which repo you are contributing to.

=== "integrations-extras and marketplace"


    Every PR must add a changelog entry to each integration that has had its shipped code modified.

    Each integration that can be installed on the Agent has its own `CHANGELOG.md` file at the root of its
    directory. Entries accumulate under the `Unreleased` section and at release time get put under their own
    section. For example:

    ```markdown
    # CHANGELOG - Foo

    ## Unreleased

    ***Changed***:

    * Made a breaking change ([#9000](https://github.com/DataDog/repo/pull/9000))

        Here's some extra context [...]

    ***Added***:

    * Add a cool feature ([#42](https://github.com/DataDog/repo/pull/42))

    ## 1.2.3 / 2081-04-01

    ***Fixed***:

    ...
    ```

    For changelog types, we adhere to those defined by [Keep a Changelog][keepachangelog-types]:

    - `Added` for new features or any non-trivial refactors.
    - `Changed` for changes in existing functionality.
    - `Deprecated` for soon-to-be removed features.
    - `Removed` for now removed features.
    - `Fixed` for any bug fixes.
    - `Security` in case of vulnerabilities.

    The first line of every new changelog entry must end with a link to the PR in which the change
    occurred. To automatically apply this suffix to manually added entries, you may run the
    [`release changelog fix`](../ddev/cli.md#ddev-release-changelog-fix) command. To create new
    entries, you may use the [`release changelog new`](../ddev/cli.md#ddev-release-changelog-new)
    command.

    !!! tip
        You may apply the `changelog/no-changelog` label to remove the CI check for changelog entries.

    ??? abstract "Formatting rules"
        ### Spacing

        * There should be a blank line between each section. This means that there should be a line between the following sections of text:
        * Changelog file header
        * Unreleased header
        * Version / Date header
        * Change type (ex: fixed, added, etc)
        * Specific descriptions of changes (**Note**: Within this section, there should **not** be new lines between bullet points,)
        * `Extra spacing on line {line number}`: There is an extra blank line on the line referenced in the error.
        * `Missing spacing on line {line number}`: Add an empty line above or below the referenced line.

        ### Version header

        * The header for an integration version should be in the following format: `version number / YYYY-MM-DD / Agent Version Number`.
        The Agent version number is not necessary, but a valid version number and date are required. The first header after the
        file's title can be `Unreleased`. The content under this section is the same as any other.
        * `Version is formatted incorrectly on line {line number}`: The version you inputted is not a valid version, or there is
        no / separator between the version and date in your header.
        * `Date is formatted incorrectly on line {line number}`: The date must be formatted as YYYY-MM-DD, with no spaces in between.

        ### Content

        * The changelog header must be capitalized and written in this format: `***HEADER***:`. Note that it should be bold and italicized.
        * `Changelog type is incorrect on line {line count}`: The changelog header on that line is not one of the six valid changelog types.
        * `Changelog header order is incorrect on line {line count}`: The changelog header on that line is in the wrong order.
        Double check the ordering of the changelogs and ensure that the headers for the changelog types are correctly ordered by priority.
        * `Changelogs should start with asterisks, on line {line count}`: All changelog details below each header should be
        bullet points, using asterisks.

=== "integrations-core"

    If you are contributing to [integrations-core](https://github.com/DataDog/integrations-core) all you need to do is use the [`release changelog new`](../ddev/cli.md#ddev-release-changelog-new) command.
    It adds files in the `changelog.d` folder inside the integrations that you have modified.
    Commit these files and push them to your PR.
    
    If you decide that you do not need a changelog because the change you made won't be shipped with the Agent, add the `changelog/no-changelog` label to the PR.

