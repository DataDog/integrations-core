# Pull requests

-----

## Changelog entries

Every integration that can be installed on the Agent has its own `CHANGELOG.md` file at the root of its
directory. Entries accumulate under the `Unreleased` section and at release time get put under their own
section. For example:

```markdown
# CHANGELOG - Foo

## Unreleased

***Changed***:

* Made a breaking change (#9000)

    Here's some extra context [...]

***Added***:

* Add a cool feature (#42)

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

Every PR must add a changelog entry to each integration that has had its shipped code modified.

The first line of every new changelog entry must end with a link to the PR in which the change
occurred. To automatically apply this suffix to manually added entries, you may run the
[`release changelog fix`](../ddev/cli.md#ddev-release-changelog-fix) command. To create new
entries, you may use the [`release changelog new`](../ddev/cli.md#ddev-release-changelog-new)
command.

!!! tip
    You may apply the `changelog/no-changelog` label to remove the CI check for changelog entries.

## Separation of concerns

Every pull request should do one thing only for easier Git management. For example, if you are
editing documentation and notice an error in the shipped example configuration, you should fix the
error in a separate pull request. Doing so will enable a clean cherry-pick or revert of the bug fix
should the need arise.

## Merges

We only allow GitHub's [squash and merge][github-squash-and-merge], for 2 reasons:

1. To keep a clean Git history
1. Our release tooling relies on commits being suffixed with the PR number in order to list changes between versions
