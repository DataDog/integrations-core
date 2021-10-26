# Pre release

-----

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/12FdFGei62ZKKI/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

A new minor version of the Agent is released every 6 weeks (approximately). Each release
ships a snapshot of [integrations-core][].

## Setup

Ensure that you have configured the following:

- [GitHub](../../ddev/configuration.md#github) credentials
- [Trello](../../ddev/configuration.md#trello) credentials

## Before Freeze

1. Make a dependency update PR 1 week before freeze:
    * Create a new branch
    * Run `ddev dep updates --sync`
    * Run `ddev dep sync`
    * Create a PR with the updated dependencies
    * If CI is failing and there are compatibility reasons, investigate the errors. You may have to add the dependency to the set of [IGNORED_DEPS](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_dev/datadog_checks/dev/tooling/commands/dep.py) and revert that change.
    
    !!! tip
        Revert the changes and rerun `ddev dep updates --sync` with the `--check-python-classifiers` flag if there are many CI failures on your PR. Running it with the flag will not update a dependency to the newest version if the python classifiers do not match the marker. Although sometimes classifiers are inaccurate on PyPI and could miss a version update, using the flag does reduce errors overall.

2. Update [style dependencies](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_dev/datadog_checks/dev/plugin/tox.py) to latest versions (except if comments say otherwise) via PR. Example: `ISORT_DEP`, `BLACK_DEP`, etc.
3. Manually run and fix if needed the [base package dependency check build](https://dev.azure.com/datadoghq/integrations-core/_build?definitionId=52).
4. Check that the [master](https://dev.azure.com/datadoghq/integrations-core/_build?definitionId=29), [py2](https://dev.azure.com/datadoghq/integrations-core/_build?definitionId=38) and [base_check](https://dev.azure.com/datadoghq/integrations-core/_build?definitionId=52) builds are green.


## Freeze

At midnight (EDT/EST) on the Friday before QA week we freeze, at which point the release manager will release
all integrations with pending changes then branch off. If no new PRs are active at the end of business hours (EDT/EST), try to make the initial [release](#release) then, so that the QA process can start on the next Monday morning. 

### Release

1. Make a pull request to release [any new integrations](../integration-release.md#new-integrations), then merge it and pull `master`
1. Make a pull request to release [all changed integrations](../integration-release.md#bulk-releases), then merge it and pull `master`
    * Get 2+ thorough reviews on the changelogs. Entries should have appropriate SemVer levels (e.g. `Changed` entries must refer to breaking changes only). See also [PR guidelines](../../guidelines/pr.md).
    * Consider x-posting the PR to Agent teams that have integrations in `integrations-core`, so they can check relevant changelogs too.

!!! important
    [Update PyPI](../integration-release.md#pypi) if you released `datadog_checks_base` or `datadog_checks_dev`.


### Branch

We create a release branch on `integrations-core` at the beginning of freeze. The purpose of this branch is to track all of the integrations that are shipped with the agent for each release. The agent RCs will be built including the source code of the integrations that is on the release branch. 

1. Create a branch based on `master` named after the highest version of the Agent being released in the form `<MAJOR>.<MINOR>.x`
1. Push the branch to GitHub

### Tag

Run:

```
git tag <MAJOR>.<MINOR>.0-rc.1 -m <MAJOR>.<MINOR>.0-rc.1
git push origin <MAJOR>.<MINOR>.0-rc.1
```

## QA week

We test all changes to integrations that were introduced since the last release.

### Create items

Create an item for every change in [our board](https://trello.com/b/ICjijxr4/agent-release-sprint) using
the Trello subcommand called [testable](../../ddev/cli.md#ddev-release-trello-testable).

For example:

```
ddev release trello testable 7.17.1 7.18.0-rc.1
```
or if the tag is not ready yet:
```
ddev release trello testable 7.17.1 origin/master
```

would select all commits that were merged between the Git references.

The command will display each change and prompt you to assign a team or skip. Purely documentation changes are automatically skipped.

Cards are automatically assigned to members of [the team](../../ddev/configuration.md#card-assignment).

### Release candidates

The main Agent release manager will increment and build a new `rc` every day a bug fix needs to be tested until all QA is complete.

Before each build is triggered:

1. Merge any fixes that have been approved, then pull `master`
1. Release [all changed integrations](../integration-release.md#bulk-releases) with the exception of `datadog_checks_dev`

For each fix merged, you must cherry-pick to the [branch](#branch):

1. The commit to `master` itself
1. The release commit, so the shipped versions match the individually released integrations

After all fixes have been cherry-picked:

1. Push the changes to GitHub
1. [Tag](#tag) with the appropriate `rc` number even if there were no changes

After the RC build is done, manually run an [Agent Azure Pipeline](https://dev.azure.com/datadoghq/integrations-core/_build?definitionId=60) using the [release branch](#branch), and the latest RC built. Select the options to run both Python 2 and Python 3 tests. This will run all the e2e tests against the current agent docker RCs. 

!!! note
    Image for Windows-Python 2 might not be built automatically for each RC. In order to build it, trigger the [dev_branch-a6-windows](https://github.com/DataDog/datadog-agent/blob/1b99fefa1d31eef8631e6343bdd2a4cf2b11f82d/.gitlab/image_deploy/docker_windows.yml#L43-L61) job in the datadog-agent Gitlab pipeline building the RC (link shared by the release coordinator).

!!! note
    In some cases, the CI may be broken on both the release branch and `master` during release week due to testing limits or developement dependency changes and **not** code changes. Fixes for these issues will be merged to `master`, and if they aren't include on the release branch the Azure pipelines will fail. If these changes are only test related (no code change), the CI fixes can be cherry-picked to the release branch and don't need a release. This will ensure that the Azure pipelines only fail on code-related errors.


### Communication

The Agent Release Manager will post a [daily status](../../ddev/cli.md#ddev-release-trello-status) for the entire release cycle.
Reply in the thread with any pending PRs meant for the next RC and update the spreadsheet `PRs included in Agent RCs`. 

Since it can be hard to predict when and if a new RC will be built, it is better to cherry-pick, release, and tag new integrations for RCs proactively so the creation of RCs is not held back. If new fixes for integratioins are discovered after you have already tagged the branch, then you can always delete the tag from github and locally, release the new changes, and re-tag. 

### Logs

Each release candidate is deployed in a staging environment. We observe the `WARN` or `ERROR` level logs filtered with the facets
 `Service:datadog-agent` and `index:main` and `LogMessage` to see if any unexpected or frequent errors start occurring that was not caught
 during QA.


## Post Freeze

After QA week ends, the code freeze is lifted when all original QA cards are tested. Bugfixes will be introduced and need to be tested, but that does not block lifting the freeze. The release manager will continue
the same process outlined above, but with more complexities due to the freeze being lifted.

Notify the Agent Release Manager when code freeze ends.

### Releasing integrations off of the release branch

There are two main cases where the release manager will have to release integrations off of the release branch: the freeze has lifted and changes to an integration have been merged after freeze and before a bugfix for an RC, or a [patch release](post-release.md#patches) is required. This section will focus on the former case.

!!! note
    Sometimes, an RC will need to be made with an integration that can be released off of the release branch, and an integration that can be released off of `master`. In this case, you can make two release PRs, one for the release branch, and one for `master`. The order of creation for these does not matter. 

Follow the following steps to release an integration off of the release branch:

1. Cherry-pick the bugfix commit to the [release branch](#branch).
2. Release the integration on the release branch.
    - Make a pull request with [integration release](../integration-release.md#new-integrations), then merge it to the release branch.

    !!! important
        Remember to trigger the release pipeline and build the wheel. You can do so by [tagging the release](../../ddev/cli.md#ddev-release-tag):

            `ddev release tag <INTEGRATION>`


3. Then pull the latest release branch so your branch has both the bugfix commit and release commit.

4. [Tag](#tag) the branch with the new bumped version `<MAJOR>.<MINOR>.0-rc.<RC_NUM>`.

5. After the release has been made, make a PR to `master` with the updates to changelog, [agent release requirements](https://github.com/DataDog/integrations-core/blob/master/requirements-agent-release.txt), and `__about__.py` of the integrations that were released on the release branch.
