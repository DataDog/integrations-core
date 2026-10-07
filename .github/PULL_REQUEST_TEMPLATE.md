## Checklist before requesting review

<!--
  The `pr-description` validation (`Run Validations`) fails until every item below is ticked and
  the visible description (excluding HTML comments) is at most 3,000 characters. CI, the changelog,
  and the QA label have their own checks. Request review only once all checks pass:
  `gh pr checks <PR> --repo DataDog/integrations-core --watch`.
-->

- [ ] I self-reviewed the full diff, and this description matches the final change
  <!--
    How to verify: run `gh pr diff <PR> --repo DataDog/integrations-core`, review every changed line,
    and compare the final diff with the description below.
  -->
- [ ] Tests cover the change, or this description explains why none are needed
  <!--
    How to verify: check the diff for relevant tests and run them as described in `AGENTS.md`.
  -->
- [ ] Automated review comments, including Codex review, were addressed or answered
  <!--
    How to verify: run `gh api repos/DataDog/integrations-core/pulls/<PR>/comments` and
    `gh pr view <PR> --repo DataDog/integrations-core --json reviews,comments`, then fix each
    finding or reply with the reason no change is needed.
  -->
- [ ] I, the human author, understand this change, can explain it to reviewers, and believe it meets the [repository standards](https://github.com/DataDog/integrations-core/blob/master/AGENTS.md)
  <!-- Coding agents: never tick this item. Only the human author may tick it. -->

<!--
  QA label: PRs that only change code owned exclusively by @DataDog/agent-integrations (see
  `.github/CODEOWNERS`) always use `qa/skip-qa`, never `qa/required`.
-->

## What does this PR do?

<!-- Give a minimal but complete description of the change and how it works. -->



## Motivation

<!--
  Briefly explain why this change is needed and how it fits in: is it part of a bigger project, and
  how does it fit into it? Are there related or follow-up PRs? Link only the references a reviewer
  needs (e.g. Jira ticket, design doc, upstream docs or changelog, related PRs).
-->
