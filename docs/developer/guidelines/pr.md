# Pull requests

-----

## Title

The [release command](../ddev/cli.md#ddev-release-make) uses the title of pull requests as-is to generate changelog entries.
Therefore, be as explicit and concise as possible when describing code changes. For example, do not say `Fix typo`,
but rather something like `Fix typo in debug log messages`.

As each integration has its own release cycle and changelog, and every pull request is automatically labeled
appropriately by our CI, there is no need include the integration's name in the title.

For the [base package](../base/about.md) and [dev package](../ddev/about.md), you may want to prefix the
title with the component being modified e.g. `[openmetrics]` or `[cli]`.

## Changelog

To document your changes, you must manually apply the `changelog/<TYPE>` label. 

Unless you have applied the `changelog/no-changelog` label, you must also edit the `CHANGELOG.md` file in the integration you have modified. Below are the guidelines for the correct formatting for changelogs: 

### Spacing

* There should be one empty line between all text of different format. This means that there should be an empty line between all of the following sections of text:
  * Changelog file header
  * Unreleased header
  * Version / Date header
  * Change type (ex: fixed, added, etc)
  * Specific descriptions of changes (note: within this section itself, there should NOT be new lines between bullets)

* `Extra spacing on line {line number}`: you have an extra empty line on the line referenced in the error. There should be only one line of spacing!
* `Missing spacing on line {line number}`: you need to add an empty line to the referenced lie

### Integration Version Header

* The header for an integration version should be in the following fashion: version number / YYYY-MM-DD / Agent Version Number. The Agent version number is not necessary, but a valid version number and date are required. The first header after the file's title can be `Unreleased`. The content under this section is the same as any other. 
* `Version is formatted incorrectly on line {line number}`: The version you inputted is not a valid version, or there is no / separator between the version and date in your header.
* `Date is formatted incorrectly on line {line number}`: The date must be formatted as YYYY-MM-DD, with no spaces in between. 

### Changelog Content
* The changelog content is broken down by the different type of change that was made. For changelog types, we adhere to those defined by [Keep a Changelog][keepachangelog-types]. For each different version, they must be written in the following order, by priority:
  * ***Removed***: for now removed features.
  * ***Changed***: for changes in existing functionality.
  * ***Security***: in case of vulnerabilities.
  * ***Deprecated***: for soon-to-be removed features.
  * ***Added***: for new features or any non-trivial refactors.
  * ***Fixed***: for any bug fixes.
* The changelog header must be capitalized and written in this format: `***HEADER***:` It should be bolded and italicized!
* `Changelog type is incorrect on line {line count}`: The changelog header on that line is not one of the 6 valid changelog types
* `Changelog header order is incorrect on line {line count}`: The changelog header on that line is in the wrong order. Double check the ordering of the changelogs and ensure that the headers for the changelog types are correctly ordered by priority. 
* `Changelogs should start with asterisks, on line {line count}`: All changelog details below each header should be bullet points, using asterisks. 

Below is an example of a correctly formatted changelog:

```
# CHANGELOG - apache

## Unreleased

## 4.2.2 / 2023-07-10

***Removed***:

* Removed information
* Removed something else

***Security***:

* Added new security feature

***Fixed***:

* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).

## 4.2.1 / 2023-04-14 / Agent 7.45.0

***Fixed***:

* Fix a typo in the `disable_generic_tags` option description. See [#14246](https://github.com/DataDog/integrations-core/pull/14246).
```

!!! warning "Caveat"
    If you are fixing something that is not yet released, apply `changelog/no-changelog`.

## Separation of concerns

Every pull request should do one thing only, for many reasons:

1. **Easy Git management** - For example, if you are editing documentation and notice an error in the shipped example configuration, you
   should fix the error in a separate pull request. Doing so will enable a clean cherry-pick or revert of the bug fix should the need arise.
1. **Easier release management** - Let's consider how the [release command](../ddev/cli.md#ddev-release-make) would handle the case of
   making a code change to multiple integrations.

    - If one of the changes only fixes a typo in a code comment, that integration will still be released as indicated by the label.
    - If both changes should indeed be released but they do different things, only one integration's changelog entry would make sense.

## Merges

We only allow GitHub's [squash and merge][github-squash-and-merge], for 2 reasons:

1. To keep a clean Git history
1. Our release tooling relies on commits being suffixed with the PR number in order to list changes between versions
