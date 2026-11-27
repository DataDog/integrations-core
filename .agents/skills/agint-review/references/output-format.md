# Output Format

## Markdown Review Format

Format the final review as plain markdown and display it in the terminal. Always include the file and line number in each comment.

Use `0` as the line number when you cannot point to a single line or small range where the issue lives — for example, a file that is missing entirely, a structural concern about the whole module, or a high-level observation about what the file does or doesn't do. If you can say "the problem is at line 42", use that line number instead. The posting script posts `0` as a file-level thread, attached to the file without pinning it to a line.

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

A finding outside the diff also carries where to post it (see [Anchoring off-diff findings](#anchoring-off-diff-findings)):

```json
{
  "path": "ddev/tests/cli/ci/tests/preview_pr_comment.py",
  "start_line": 228,
  "line": 256,
  "side": "RIGHT",
  "anchor": {"path": "ddev/src/ddev/cli/ci/tests/pr_comment.py", "line": 57, "side": "RIGHT"},
  "body": "**Suggestion**: Full comment text identical to the markdown block."
}
```

**Rules:**
- `path`: the file the finding is about, relative to the repo root with no leading slash, exactly as it appears in the diff when the PR changes it
- `line`: integer from the `## [file]:[line]` header. Use `0` only when the finding has no specific location — you cannot point to a line or small range where the problem is (e.g., a missing file, a module-wide structural concern). If you can identify "the problem is at line 42", use that number. Line numbers start at 1, so `0` is the unambiguous file-level sentinel; the posting script will attach it at the file level without pinning it to a line.
- `start_line` (optional): the first line when the finding covers a range ending at `line`. The script only uses it to name the range in the reference line of a re-anchored comment; threads are never multi-line.
- `side`: always `"RIGHT"` — comments are on new/changed code; only use `"LEFT"` if the comment is explicitly about a deleted line; omit when `line` is `0`
- `anchor` (optional): `{path, line, side}`, the changed line to post at when the finding's own location isn't in the diff. `line: 0` makes it a file-level thread on `anchor.path`. See [Anchoring off-diff findings](#anchoring-off-diff-findings).
- `body`: if a block has multiple types at the same file+line (e.g., both a **Request** and a **Suggestion**), combine into ONE entry with both separated by a blank line — never two entries for the same file+line
- Start every finding with its type label exactly as written in `references/comment-style.md` (`**Request**`, `**Suggestion**`, `**Question**`, `**Nit**`, `**Follow-up**`). The posting script counts these labels for the count line and picks the review event from them; the Slack review coordinator counts `**Request**`.

**Line snapping**: When the script posts line-level comments, it snaps each line number to the nearest line present in the PR diff on the comment's side, as long as it's at most 5 lines away. You do not need to do this snapping yourself — just use the line number from the code. Use `0` only when the finding genuinely has no specific location.

**Follow-ups**: locate them like any other finding, on the line where the pre-existing problem lives. That line is often outside the diff; give them an `anchor` (below).

This pass happens AFTER the markdown is finalized — do not try to build JSON and markdown simultaneously.

### Anchoring off-diff findings

Every finding is posted as a review thread the author can reply to and resolve, and GitHub only accepts threads on files the PR changes, at lines in the diff (changed lines and the context lines of their hunks, `<review_dir>/diff.full`) or at the file level. A finding is off-diff when its file isn't in the diff, or when its line is more than 5 lines from the nearest diff line on its side. For each one:

- Keep `path`, `line` (and `start_line`) on the real target, the code the finding is about.
- Set `anchor` to the changed line most related to it: the call the PR changed, the change that makes the unchanged code relevant, the added line after which something is missing. When no changed line is related but a changed file is, use that file with `line: 0`.
- Don't write where the comment really applies; the script adds it. A re-anchored comment's body starts with a line naming the real file and lines, linked at the reviewed commit, e.g. _About [`ddev/tests/cli/ci/tests/preview_pr_comment.py` L228-L256](…), which this PR doesn't change._ Write the body so it reads correctly under that line.

Without a usable `anchor` (missing, or not in the diff), the script picks one: the nearest changed line of the same file, or, for a file outside the diff, a file-level thread on the changed file nearest to it in the tree. That's a guess, so set `anchor` yourself. A comment goes into the review body only when GitHub rejects its thread or the diff can't be read.

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
