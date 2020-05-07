# Contributing

First of all, thanks for contributing!

This document provides some basic guidelines for contributing to this repository.
To propose improvements, feel free to submit a PR.

## Submitting issues

* If you have a feature request, you should [contact support][3] so the request 
can be properly tracked.
* If you think you've found an issue, please search the [Troubleshooting][1]
  section of our [Knowledge base][2] to see if it's known.
* If you can't find anything useful, please contact our [support][3] and
  [send them your logs][4].
* Finally, you can open a Github issue.

## Pull Requests

Have you fixed a bug or written a new check and want to share it? Many thanks!

In order to ease/speed up our review, here are some items you can check/improve
when submitting your PR:

* Have a [proper commit history](#commits) (we advise you to rebase if needed).
* Write tests for the code you wrote.
* Make sure that all tests pass locally.
* Summarize your PR with a meaningful title, [see later on this doc](#pull-request-title).
* Add the most suitable changelog label choosing one of the following:
  * `changelog/Added` for new features.
  * `changelog/Changed` for changes in existing functionality.
  * `changelog/Deprecated` for soon-to-be removed features.
  * `changelog/Removed` for now removed features.
  * `changelog/Fixed` for any bug fixes.
  * `changelog/Security` in case of vulnerabilities.
  * `changelog/no-changelog` in case this PR should not appear in the changelog at all.

See [here][5] for more details about changelogs.

Your pull request must pass all CI tests before we will merge it. If you're seeing
an error and don't think it's your fault, it may not be! [Join us on Slack][6]
or send  us an email, and together we'll get it sorted out.

### Keep it small, focused

Avoid changing too many things at once. For instance if you're fixing two different
checks at once, it makes reviewing harder and the _time-to-release_ longer.

### Pull Request title

Unless the PR is marked with the proper exclusion label, the title will be used
to automatically fill the changelog entries. For this reason the title must be
concise but explanatory.

### Commit Messages

Please don't be this person: `git commit -m "Fixed stuff"`. Take a moment to
write meaningful commit messages.

The commit message should describe the reason for the change and give extra details
that will allow someone later on to understand in 5 seconds the thing you've been
working on for a day.

If your commit is only shipping documentation changes or example files, and is a
complete no-op for the test suite, please prepend the commit message with the
string `[skip ci]` to skip the build and test and give that slot to someone else
who does need it.

If your commit is testing possible backward-incompatible changes to the base package
or many integrations at once, you can preface a commit message with `[ci run all]` to
test everything at once in separate runners, thus avoiding timeouts.

### Squash your commits

Please rebase your changes on `master` and squash your commits whenever possible,
it keeps history cleaner and it's easier to revert things. It also makes developers
happier!

## Integrations Extras

For new integrations, please open a pull request in the [integrations-extras][7] repo.

[1]: https://datadog.zendesk.com/hc/en-us/sections/200766955-Troubleshooting
[2]: https://datadog.zendesk.com/hc/en-us
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/troubleshooting/#send-a-flare
[5]: https://keepachangelog.com/en/1.0.0
[6]: https://datadoghq.slack.com
[7]: https://github.com/DataDog/integrations-extras
