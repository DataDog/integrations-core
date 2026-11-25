# Review tenets

How every reviewer reviews, whatever its area. Your agent file says what to check; these say how. The challenger checks every finding against them.

1. **Review as an expert, not a checklist.** Your rules are minimums, not the boundary. Raise anything wrong in your area, listed or not.
2. **Stay in your area, but don't drop real problems.** Don't restate rules another agent owns (what `AGENTS.md` says belongs to `conventions`). If you find a real problem and aren't sure it's yours, raise it; the challenger merges overlapping findings.
3. **Review what the PR changes.** An existing problem is in scope only when the PR makes it worse or depends on it. Otherwise it's a Follow-up.
4. **Don't repeat CI.** Skip what `ddev validate all`, ruff, pinact, dependency review or the size diff already catch.
5. **Verify before claiming.** Read the full file in both worktrees, grep for callers, check the product's docs for product claims. Every finding cites its evidence. What you can't verify is a Question.
6. **Severity has to be defensible.** A Request means it must change before merge, and you can say what breaks if it doesn't. When unsure, ask; if you can't defend it, drop it. A false Request costs the author more than a missed Suggestion.
   See [Severity by repository](#severity-by-repository): outside integrations-core the bar for a Request is higher.
7. **Actionable comments; a clean review is fine.** Why, then what to change, on the exact lines. The same pattern once, listing the other places. Zero findings is a valid review.
8. **Fix the cause, not the symptom.** Before raising a defect, work out why it exists. When the PR's fix, or the one you'd suggest, only covers the case in front of you (one more edge case, one more special-cased value), say what makes the code fragile and ask for that to change. When the cause is outside the PR's scope, ask for the narrow fix and raise the cause as a Follow-up (tenet 3).

## Severity by repository

The repository is in your prompt (`<repository>`). Tenet 6 applies everywhere; how high a finding can go depends on the repo:

- **integrations-core:** the severities in your agent file, as written.
- **integrations-extras, marketplace and integrations-internal:** a **Request** only for a security issue or something actually broken: it fails, sends wrong data, or confuses or harms users. Everything else is at most a **Suggestion** or a **Nit**: tests, conventions, style, structure, a missing E2E environment, the `datadog_checks_base` pin, `check-types` and the like. No Requests for tests.
- **Any other repository:** as integrations-core.
- Rules that exist because of how integrations-core works (E2E required for new integrations, the `datadog_checks_base` pin, `check-types`) still apply on the other repos, but never above **Suggestion**.
