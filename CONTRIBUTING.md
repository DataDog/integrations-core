# Contributing

First of all, thanks for contributing!

This document provides some basic guidelines for contributing to this repository.
To propose improvements, feel free to submit a PR.

## Submitting issues

* If you have a feature request, you should [contact support][3] so the request 
can be properly tracked.
* If you think you've found an issue, please check the [Agent troubleshooting
  guide][1] and search our [Knowledge base][2] to see if it's known.
* If you can't find anything useful, please contact our [support][3] and
  [send them your logs][4].
* Finally, you can open a Github issue.

## Pull Requests

Have you fixed a bug or written a new check and want to share it? Many thanks!

* Fill in the [pull request template][9]. Merge is blocked until every item in its
  _Checklist before requesting review_ is ticked and the description is at most 3,000
  characters (HTML comments excluded).
* Keep the description minimal but complete, and link only the references a reviewer needs
  (for example the related issue, upstream docs, or related PRs).
* Write tests for the code you wrote, and make sure they pass locally.
* Request review only once all CI checks pass. If you're seeing an error and don't think
  it's your fault, it may not be! [Join us on Slack][6] or send us an email, and together
  we'll get it sorted out.
* Add a changelog entry with `ddev release changelog new` for any change shipped with the
  Agent, [see here for more][8].
* Understand your change well enough to explain it to reviewers, including any part
  written with AI assistance.

The detailed conventions for code, configuration, and pull requests live in [AGENTS.md][10]
and the [pull request guidelines][8].

### Keep it small, focused

Avoid changing too many things at once. For instance if you're fixing two different
checks at once, it makes reviewing harder and the _time-to-release_ longer.

### Pull Request title

Pull requests are squash-merged, so the title becomes the commit message on `master`.
Keep it short and descriptive in plain words, for example `Add TLS support to the Kafka check`
rather than `Fixed stuff`.

## Integrations Extras

For new integrations, please open a pull request in the [integrations-extras][7] repo.

[1]: https://docs.datadoghq.com/agent/troubleshooting/
[2]: https://help.datadoghq.com/hc/en-us
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/
[6]: https://datadoghq.slack.com
[7]: https://github.com/DataDog/integrations-extras
[8]: https://datadoghq.dev/integrations-core/guidelines/pr
[9]: .github/PULL_REQUEST_TEMPLATE.md
[10]: AGENTS.md
