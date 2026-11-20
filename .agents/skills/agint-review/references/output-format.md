# Output Format

## Markdown Review Format

Format the final review as plain markdown and display it in the terminal. Always include the file and line number in each comment.

Use `0` as the line number when you cannot point to a single line or small range where the issue lives — for example, a file that is missing entirely, a structural concern about the whole module, or a high-level observation about what the file does or doesn't do. If you can say "the problem is at line 42", use that line number instead. The posting script treats `0` as a file-level comment and attaches it to the file without pinning it to a line.

```markdown
# PR Review: #[number] — "[title]"

## Summary
[2-3 sentence overview: what the PR does, overall impression, key concerns if any]

## [filename.py]:[line_number]

**Request**: [comment text with specific line references]

**Suggestion**: [comment text]

**Follow-up**: [a pre-existing problem this PR didn't introduce or make worse]

## [another_file.py]:[line_number]

**Nit**: [comment text]

## [.github/workflows/release.yml]:[line_number]

**Request**: [comment text]

## [config.yaml]:0

**Request**: [finding that applies to the file as a whole, not to a specific line — any severity type is valid here]

---

**Review complete.** [X] comments across [Y] files: [N] requests, [N] suggestions, [N] questions, [N] nits, [N] follow-ups.

**Challenger**: [N] kept, [N] demoted, [N] dropped, [N] contested.
```

**Ordering within each file:**
1. Requests first (blockers)
2. Suggestions
3. Questions
4. Nits
5. Follow-ups last

**Suppressed comments** — if the user asks to see what was dropped (e.g., *"show me the suppressed comments"*), show this section in the terminal. It is never posted to GitHub:

```markdown
<details>
<summary>Suppressed comments ([N] dropped by challenger)</summary>

## [filename.py]:[line_number]
**[Original severity]** _(dropped: [challenger's reason])_: [original finding text]

...
</details>
```

---

## JSON Payload Schema

After completing the full markdown synthesis, produce a JSON comments array as a second pass. For each `## [file]:[line]` block in the review, create one JSON entry:

```json
{
  "path": "relative/path/to/file.py",
  "line": 42,
  "side": "RIGHT",
  "body": "**Request**: Full comment text identical to the markdown block."
}
```

**Rules:**
- `path`: file path exactly as it appears in the diff (relative to repo root, no leading slash)
- `line`: integer from the `## [file]:[line]` header. Use `0` only when the finding has no specific location — you cannot point to a line or small range where the problem is (e.g., a missing file, a module-wide structural concern). If you can identify "the problem is at line 42", use that number. Line numbers start at 1, so `0` is the unambiguous file-level sentinel; the posting script will attach it at the file level without pinning it to a line.
- `side`: always `"RIGHT"` — comments are on new/changed code; only use `"LEFT"` if the comment is explicitly about a deleted line; omit when `line` is `0`
- `body`: if a block has multiple types at the same file+line (e.g., both a **Request** and a **Suggestion**), combine into ONE entry with both separated by a blank line — never two entries for the same file+line
- Start every finding with its type label exactly as written in `references/comment-style.md` (`**Request**`, `**Suggestion**`, `**Question**`, `**Nit**`, `**Follow-up**`). The posting script counts these labels for the count line and picks the review event from them; the Slack review coordinator counts `**Request**`.

**Line snapping**: When the script posts line-level comments, it snaps each line number to the nearest line present in the PR diff. If the nearest diff line is more than 5 lines away, the comment is automatically promoted to file-level. You do not need to do this snapping yourself — just use the line number from the code. Use `0` only when the finding genuinely has no specific location.

**Follow-ups**: anchor them like any other finding, on the line where the pre-existing problem lives. When that line is outside the diff, the script moves the comment to the review body (see below), which is expected.

**Anchoring off-diff findings**: GitHub only renders inline comments on lines that appear in the diff (changed lines and their surrounding context within a hunk). When the finding is about something off-diff — a missing entry, an unchanged function the change has implications for, an item that should appear after a particular added line — pick the **last related added/changed line** in that file as the anchor and state the actual target explicitly in the body (e.g. _"After line 411, add…"_, _"This refers to the unchanged `validate()` at line 220…"_). The comment must read correctly even if the reader doesn't notice the pin position. If you cannot identify any changed line nearby, use `0` and let the script attach it as a file-level comment. If the file isn't in the diff at all, the script will move the comment to the review body automatically — write it so it makes sense without an anchor.

This pass happens AFTER the markdown is finalized — do not try to build JSON and markdown simultaneously.

### Full payload structure

Write to `<review_dir>/review.json` (from `context.json`):

```json
{
  "pr_number": <PR_NUMBER>,
  "repo": "<REPO>",
  "commit_sha": "<COMMIT_SHA>",
  "author": "<PR_AUTHOR>",
  "comments": [ ... array from above ... ],
  "uncovered_files": [ ... ]
}
```

`uncovered_files` is only written when setup found no reviewer for the PR (`context.json.agents_to_run` empty on a full review): copy `context.json.uncovered_files` there and leave `comments` empty. Omit it otherwise.

`gh-post-review` picks the review event from the comment labels: `REQUEST_CHANGES` when any comment has a `**Request**`, `COMMENT` otherwise (Follow-ups never count as Requests). It never approves. An empty `comments` array is valid: the review is still posted, with "No comments" in the body.
