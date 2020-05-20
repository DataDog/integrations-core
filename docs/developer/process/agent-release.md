# Agent release

-----

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/12FdFGei62ZKKI/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

A new minor version of the Agent is released every 6 weeks (approximately). Each release
ships a snapshot of [integrations-core][].

## Setup

Configure and add the following to your [configuration](../ddev/configuration.md):

- [GitHub](../ddev/configuration.md#github) credentials
- [Trello](../ddev/configuration.md#trello) credentials
- Add the `trello_users_$team` table to [automatically assign test cards](#create-items) to team members.

## Freeze

At midnight (EDT/EST) on the Friday before QA week we freeze, at which point the release manager will release
all integrations with pending changes then branch off.

### Release

1. Make a pull request to release [any new integrations](integration-release.md#new-integrations), then merge it and pull `master`
1. Make a pull request to release [all changed integrations](integration-release.md#bulk-releases), then merge it and pull `master`

!!! important
    Update [PyPI](integration-release.md#PyPI) if you released `datadog_checks_base` or `datadog_checks_dev`.
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
the Trello subcommand called [testable](../ddev/cli.md#testable).

For example:

```
ddev release trello testable 7.17.1 7.18.0-rc.1
```

would select all commits that were merged between the Git references.

The command will display each change and prompt you to assign a team or skip. Purely documentation changes are automatically skipped.

You must assign each item to a team member after creation and ensure no one is assigned to a change that they authored.

If you would like to automate this, then add a `trello_users_$team` table in your [configuration](../ddev/configuration.md), with
keys being GitHub usernames and values being their corresponding Trello IDs (not names). You can find current team member information
in [this document](https://github.com/DataDog/devops/wiki/GitHub-usernames-and-Trello-IDs).

### Release candidates

The main Agent release manager will increment and build a new `rc` every day a bug fix needs to be tested until all QA is complete.

Before each build is triggered:

1. Merge any fixes that have been approved, then pull `master`
1. Release [all changed integrations](integration-release.md#bulk-releases) with the exception of `datadog_checks_dev`

For each fix merged, you must cherry-pick to the [branch](#branch):

1. The commit to `master` itself
1. The release commit, so the shipped versions match the individually released integrations

After all fixes have been cherry-picked:

1. Push the changes to GitHub
1. [Tag](#tag) with the appropriate `rc` number even if there were no changes

### Communication

Update the `#agent-release-sync` channel with a daily status.
The Agent Release Manager will post a [daily status](../ddev/cli.md#status) for the entire release cycle.

```
#agent-integrations status:
1. Status of the testing: [cards left | finished]
2. Bugs found pending to fix: [description of bugs]
3. Fixes done pending a new RC build: [link PRs of fixes]
```

## Release week

After QA week ends the code freeze is lifted, even if there are items yet to be tested. The release manager will continue
the same process outlined above.

## Finalize

On the day of the final stable release, [tag](#tag) the [branch](#branch) with `<MAJOR>.<MINOR>.0`.

After the main Agent release manager confirms successful deployment to a few targets, create a branch based on `master` and run:

```
ddev agent changelog
ddev agent integrations
```

Update the [`AGENT_CHANGELOG`][agent-changelog] and [`AGENT_INTEGRATIONS`][agent-integrations] files. Create a pull request and wait for approval before merging.
