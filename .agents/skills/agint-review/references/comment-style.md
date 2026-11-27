# Comment style

How review comments are worded. Every reviewer has this in its instruction paths; the challenger reads it when judging findings; the orchestrator follows it during synthesis. What makes a comment worth posting (verified, defensible, actionable) is in `tenets.md`; this file only covers the wording. If you find these rules duplicated anywhere else, that copy is wrong.

A good review comment reads like one a colleague wrote.

## Wording

- **First person, professional and personal.** "I'd rename this," "I noticed," "I think this could…" Not "the code should," not "it is recommended that." A reviewer is a person, not a linter.
- **Name things exactly.** Exact lines, variable names, function names: "the `tag_list` initialization at `check.py:45`", not "the initialization."
- **Be proportional.** A typo is a one-line nit, not a paragraph. A subtle race condition deserves the paragraph.
- **Show the fix briefly.** A short excerpt of what good looks like (10–20 lines at most, never a full rewrite) beats three sentences of prose.
- **No hedged claims.** Never write "likely includes," "probably handles," or "should already be covered." Either you checked it, or it's a Question.
- **No compliments.** A comment asks for something or flags something. If there's nothing to change, ask or follow up on, don't write it.
- **Say when it's pre-existing.** A Follow-up says that the problem was already there before this PR and can go in a later PR or ticket.

## Comment types

Every comment has exactly one of these five types. Pick the one that matches the actual stakes; don't inflate.

| Type | Use when |
|------|----------|
| **Request** | A change you believe must happen before merging: a bug, a security issue, a contract violation, a hard-to-reverse mistake. |
| **Suggestion** | An improvement you'd recommend but wouldn't block on. |
| **Question** | The intent isn't clear, or the claim can't be verified. Ask before assuming. |
| **Nit** | Minor naming, formatting or style. The synthesis drops these on PRs where the severity floor filters them out. |
| **Follow-up** | Something wrong that this PR didn't introduce and doesn't make worse. Not blocking; it's for a later PR or ticket. Never counted as a Request. |

When findings from several agents about the same line are merged, the highest type wins. When demoting (per challenger verdict), reduce by exactly one level (Request → Suggestion → Nit). A Follow-up is never promoted to a Request; if the PR does make the problem worse, it was never a Follow-up.

Write the type exactly as shown, in bold, at the start of the comment, followed by a colon and a space: `**Request**: …`, `**Follow-up**: …`. The posting script counts comments by these labels, and the Slack review coordinator counts the `**Request**` ones.
