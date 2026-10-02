## Checklist before requesting review

<!--
  Merge is blocked until every item below is ticked and the visible description (excluding HTML
  comments) is at most 3,000 characters.
-->

- [ ] All other CI checks have finished and passed
  <!--
    Validation: Run `gh pr checks <PR> --repo DataDog/integrations-core --watch` and verify every
    check except `Check PR description` passes. Investigate failures and push fixes before requesting review.
    Coding agents: Tell the user you are watching CI because all checks must pass before review,
    then run the command above. If it times out, relaunch it until all checks finish.
  -->
- [ ] Exactly one of the `qa/required` or `qa/skip-qa` labels is set
  <!--
    Validation: Run `gh pr view <PR> --repo DataDog/integrations-core --json labels` and verify
    exactly one of these labels is present. Changes to code owned by @DataDog/agent-integrations
    (see `.github/CODEOWNERS`) are `qa/skip-qa` by default; use `qa/required` only when the change
    needs QA validation.
  -->
- [ ] A changelog entry is present where required
  <!--
    Validation: Review the changed files against the Changelog Management rules in `AGENTS.md`.
    For changes that require one, verify `<INTEGRATION>/changelog.d/<PR_NUMBER>.<TYPE>` exists and
    that `Check PR changelog` passes in `gh pr checks <PR> --repo DataDog/integrations-core`.
  -->
- [ ] Tests were added or updated for the feature or bugfix
  <!--
    Validation: Review the diff for relevant tests and run the focused test command from
    `AGENTS.md`, such as `ddev --no-interactive test <INTEGRATION>`. For changes that are neither a
    feature nor a bugfix, verify this item is not applicable before ticking it.
  -->
- [ ] Automated review bot comments, including Codex review, were addressed or answered
  <!--
    Validation: Run `gh pr view <PR> --repo DataDog/integrations-core --json reviews,comments` and
    `gh api repos/DataDog/integrations-core/pulls/<PR>/comments`, then resolve each bot finding or
    reply with the reason no change is needed.
  -->
- [ ] I self-reviewed the full diff, and this description matches the final change
  <!--
    Validation: Run `gh pr diff <PR> --repo DataDog/integrations-core`, review every changed line,
    and compare the final diff with the description below.
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
