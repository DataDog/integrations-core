# Pull requests

-----

## Title

The [release command](../ddev/cli.md#make) uses the title of pull requests as-is to generate changelog entries.
Therefore, be as explicit and concise as possible when describing code changes. For example, do not say `Fix typo`,
but rather something like `Fix typo in debug log messages`.

As each integration has its own release cycle and changelog, and every pull request is automatically labeled
appropriately by our CI, there is no need include the integration's name in the title.

For the [base package](../base/about.md) and [dev package](../ddev/about.md), you may want to prefix the
title with the component being modified e.g. `[openmetrics]` or `[cli]`.

## Changelog label

Our [labeler](../meta/ci.md#labeler) will automatically detect if changes would not impact shipped code and
apply `changelog/no-changelog`. In all other cases, you must manually apply `changelog/<TYPE>`.

For changelog types, we adhere to those defined by [Keep a Changelog][keepachangelog-types]:

- `Added` for new features or any non-trivial refactors.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

!!! warning "Caveat"
    If you are fixing something that is not yet released, apply `changelog/no-changelog`.

## Separation of concerns

Every pull request should do one thing only, for many reasons:

1. **Easy Git management** - For example, if you are editing documentation and notice an error in the shipped example configuration, you
   should fix the error in a separate pull request. Doing so will enable a clean cherry-pick or revert of the bug fix should the need arise.
1. **Easier release management** - Let's consider how the [release command](../ddev/cli.md#make) would handle the case of
   making a code change to multiple integrations.

    - If one of the changes only fixes a typo in a code comment, that integration will still be released as indicated by the label.
    - If both changes should indeed be released but they do different things, only one integration's changelog entry would make sense.

## Merges

To keep a clean Git history we disable standard merges and use GitHub's [squash and merge][github-squash-and-merge].

You may [rebase and merge][github-rebase-and-merge] only if all of the following conditions are true:

1. the change is massive and cannot be broken into multiple pull requests
1. retaining the history of commits is actually deemed to be important
1. the commits are curated so each represents a distinct change
