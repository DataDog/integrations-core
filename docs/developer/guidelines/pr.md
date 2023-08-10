# Pull requests

-----

## Changelog entries

Every PR must add a changelog entry to each integration that has had its shipped code modified.

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

Unless you have applied the `changelog/no-changelog` label, you must also edit the `CHANGELOG.md` file in 
the integration you have modified. Below are the guidelines for the correct formatting for changelogs: 

### Spacing

* There should be one empty line between all text of different format. This means that there should be an 
empty line between all of the following sections of text:
  * Changelog file header
  * Unreleased header
  * Version / Date header
  * Change type (ex: fixed, added, etc)
  * Specific descriptions of changes (note: within this section itself, there should NOT be new lines between bullets)

* `Extra spacing on line {line number}`: There is an extra blank line on the line referenced in the error. 
* `Missing spacing on line {line number}`: Add an empty line above or below the referenced line.

### Integration Version Header

* The header for an integration version should be in the following fashion: `version number / YYYY-MM-DD / Agent Version Number`. 
The Agent version number is not necessary, but a valid version number and date are required. The first header after the 
file's title can be `Unreleased`. The content under this section is the same as any other. 
* `Version is formatted incorrectly on line {line number}`: The version you inputted is not a valid version, or there is 
no / separator between the version and date in your header.
* `Date is formatted incorrectly on line {line number}`: The date must be formatted as YYYY-MM-DD, with no spaces in between. 

### Changelog Content
* The changelog content is broken down by the different type of change that was made. For changelog types, we adhere 
to those defined by [Keep a Changelog][keepachangelog-types]. For each different version, they must be written in the 
following order, by priority:
  * ***Removed***: for now removed features.
  * ***Changed***: for changes in existing functionality.
  * ***Security***: in case of vulnerabilities.
  * ***Deprecated***: for soon-to-be removed features.
  * ***Added***: for new features or any non-trivial refactors.
  * ***Fixed***: for any bug fixes.
* The changelog header must be capitalized and written in this format: `***HEADER***:` It should be bolded and italicized!
* `Changelog type is incorrect on line {line count}`: The changelog header on that line is not one of the 6 valid changelog types
* `Changelog header order is incorrect on line {line count}`: The changelog header on that line is in the wrong order. 
Double check the ordering of the changelogs and ensure that the headers for the changelog types are correctly ordered by priority. 
* `Changelogs should start with asterisks, on line {line count}`: All changelog details below each header should be 
bullet points, using asterisks. 
* The first line of every new changelog entry must end with a link to the PR in which the change
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
