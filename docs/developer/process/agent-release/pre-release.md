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
- [Trello team mappings](../../ddev/configuration.md#card-assignment)

## Freeze

At midnight (EDT/EST) on the Friday before QA week we freeze, at which point the release manager will release
all integrations with pending changes then branch off.

### Release

1. Make a pull request to release [any new integrations](../integration-release.md#new-integrations), then merge it and pull `master`
1. Make a pull request to release [all changed integrations](../integration-release.md#bulk-releases), then merge it and pull `master`

!!! important
    [Update PyPI](../integration-release.md#pypi) if you released `datadog_checks_base` or `datadog_checks_dev`.


### Branch

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
the Trello subcommand called [testable](../../ddev/cli.md#testable).

For example:

```
ddev release trello testable 7.17.1 7.18.0-rc.1
```

would select all commits that were merged between the Git references.

The command will display each change and prompt you to assign a team or skip. Purely documentation changes are automatically skipped.

Cards are automatically assigned if `$trello_users_$team` table is [configured](../../ddev/configuration.md#card-assignment).

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

### Communication

The Agent Release Manager will post a [daily status](../../ddev/cli.md#status) for the entire release cycle.

```
#agent-integrations status:
1. Status of the testing: [cards left | finished]
2. Bugs found pending to fix: [description of bugs]
3. Fixes done pending a new RC build: [link PRs of fixes]
```

### Logs

Each release candidate is deployed in a staging environment. We observe the `WARN` or `ERROR` level logs filtered with the facets
 `Service:datadog-agent` and `index:main` and `LogMessage` to see if any unexpected or frequent errors start occurring that was not caught
 during QA.
 
 
## Release week

After QA week ends the code freeze is lifted, even if there are items yet to be tested. The release manager will continue
the same process outlined above.
