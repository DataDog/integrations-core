# Integration release

Each Agent integration has its own release cycle. Many integrations are actively developed and released often while
some are rarely touched (usually indicating feature-completeness).

## Versioning

All releases adhere to [Semantic Versioning][semver-home].

Tags in the form `<INTEGRATION_NAME>-<VERSION>` are added to the Git repository. Therefore, it's
possible to checkout and build the code for a certain version of a specific check.

## Setup

[Configure](../ddev/configuration.md#github) your GitHub auth.

## Identify changes

!!! note
    If you already know which integration you'd like to release, skip this section.

To see all checks that need to be released, run `ddev release show ready`.

1. Checkout and pull the most recent version of the `master` branch.

    ```
    git checkout master
    git pull
    ```

    !!! danger "Important"
        Not using the latest version of `master` may cause errors in the build pipeline.

2. Review which PRs were merged in between the latest release and the `master` branch.

    ```
    ddev release show changes <INTEGRATION>
    ```

    You should ensure that PR titles and changelog labels are correct.

## Creating the release

1. Create a release branch from master (suggested naming format is `<USERNAME>/release-<INTEGRATION_NAME>`).
   This has the purpose of opening a PR so others can review the changelog.

    !!! danger "Important"
        It is critical the branch name is not in the form `<USERNAME>/<INTEGRATION_NAME>-<NEW_VERSION>` because one of
        our Gitlab jobs is triggered whenever a Git reference matches that pattern, see !3843 & !3980.

2. Make the release (Third party integrations).
    * Update the version on `datadog_checks/<INTEGRATION>/__about__.py`.

    * Update the CHANGELOG.md file This file can be automatically updated by `ddev` using the following command:

    ```
    ddev release changelog <INTEGRATION_NAME> <VERSION>
    ```

    This command will list all merged PRs since the last release and creates a changelog entry based on the pull request labels,
    this means that *the version bump needs to be on a separate PR from the one that included the changes*.
    For changelog types, we adhere to those defined by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/#how).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |


3. Push your branch to GitHub and create a pull request.

    1. Update the title of the PR to something like `[Release] Bumped <INTEGRATION> version to <VERSION>`.
    1. Ask for a review in Slack.

4. Merge the pull request after approval or wait for it to be merged.

## Metadata

You need to run certain backend jobs if any changes modified integration metadata or assets such as dashboards.
If you are a contributor a datadog employee will handle this.

## New integrations (third party integrations)

For first time releases of third party integrations, simply merge the integration to master and a release will be
triggered with the specified version number in the about file.
