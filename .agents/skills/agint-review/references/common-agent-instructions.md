# Reviewer output contract

What every reviewer writes to its findings file. How to review is in `tenets.md` and how to word a comment is in `comment-style.md`; both are in your instruction paths too. When your agent file and this contract disagree on the shape of the output, this contract wins.

## Finding fields

Write your findings as a list. Each finding has these fields:

```
- **file:** `path/to/file.py`
  **lines:** 42-50
  **category:** Request | Suggestion | Question | Nit | Follow-up
  **finding:** [What's wrong, why it matters, and what to change]
  **evidence:** [Where the claim comes from: see below]
```

- `file`: the path relative to the repository root, as it appears in the diff.
- `lines`: a line or range in the head tree. For a line the PR deleted, use the nearest line of the head tree and say so in the finding.
- `category`: the comment type from `comment-style.md`. Pick it with tenet 6.
- `finding`: written to the author, following `comment-style.md`.
- `evidence`: see [Evidence](#evidence).

### The `N/A` rule

Use `N/A` for `lines` only when the finding has no single place to point at: a file that is missing entirely, or a concern about the whole file. If you can say "line 42 is where this shows up", use line 42. The orchestrator turns `N/A` into a file-level comment that isn't pinned to a line.

## Evidence

Every finding has evidence: a pointer to what proves the claim, never a restatement of the finding.

- **Code you read:** `check.py:45 (head): tag_list is never initialized`, `read base/foo/conf.yaml.example: no retry option`.
- **A caller or use you found:** `grep in head: 3 callers of get_client(), none pass timeout (bar/check.py:88, …)`.
- **An external source:** the URL and what it says, e.g. `https://docs.example.com/api/v3#containers: /containers is read-only`.
- **A rule:** the file and section it lives in, e.g. `AGENTS.md › Python Code Style › Type Hints` or `references/ddev/output.md › Common failure modes`. Cite only a rule you read in that file. When you're unsure where a rule lives, leave the citation out and point at the code instead: a wrong citation can sink a correct finding.

`conventions` cites `AGENTS.md` by design. The other agents cite their own references or the code, and don't restate `AGENTS.md` rules (tenet 2).

## Concerns the scout flagged

The scout context has a "Description vs. diff consistency" section. A concern flagged there that falls in your area is a candidate finding, not background reading: either raise it at the severity it deserves, or close it in one line in your closing note ("considered X: not a finding because Y"). Don't skip it silently.

## A clean review

When you have no findings, write one line saying so, then a short list of the areas or reference files you checked, each with the lines that satisfied it. Don't list every behaviour you confirmed is correct, and don't restate the scout context.

When you have findings, the list is the body. A note on what you checked that came up clean is one short closing paragraph, not a second list.
