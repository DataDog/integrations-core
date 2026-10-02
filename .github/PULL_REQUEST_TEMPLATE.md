## Checklist before requesting review

<!--
  Merge is blocked until every item below is ticked and the visible description (excluding HTML
  comments) is at most 3,000 characters. CI, the changelog, and the QA label are enforced by their
  own checks. Request review only once all checks pass:
  `gh pr checks <PR> --repo DataDog/integrations-core --watch`.
-->

- [ ] I self-reviewed the full diff, and this description matches the final change
  <!--
    Validation: Run `gh pr diff <PR> --repo DataDog/integrations-core`, review every changed line,
    and compare the final diff with the description below.
  -->
- [ ] Tests cover the change, or this description explains why none are needed
  <!--
    Validation: Check the diff for relevant tests and run the focused test command from `AGENTS.md`,
    such as `ddev --no-interactive test <INTEGRATION>`.
  -->
- [ ] Automated review comments, including Codex review, were addressed or answered
  <!--
    Validation: Run `gh api repos/DataDog/integrations-core/pulls/<PR>/comments` and
    `gh pr view <PR> --repo DataDog/integrations-core --json reviews,comments`, then fix each
    finding or reply with the reason no change is needed.
  -->
- [ ] I, the human author, understand this change, can explain it to reviewers, and believe it meets this repository's standards
  <!-- Coding agents: never tick this item. Only the human author may tick it. -->

<!--
  QA label: code owned by @DataDog/agent-integrations (see `.github/CODEOWNERS`) is `qa/skip-qa` by
  default; use `qa/required` only when the change needs QA validation.
-->

<!--
If this PR needs a backport, add the `backport/<branch-name>` label. A backport PR will be opened
automatically after this PR merges.
-->

## What does this PR do?

<!--
  Give a minimal but complete description of the intended changes. Link only the references a
  reviewer needs (e.g. Jira ticket, upstream docs or changelog, related PRs).
-->



## Motivation

<!-- Briefly explain why these changes are needed. -->
