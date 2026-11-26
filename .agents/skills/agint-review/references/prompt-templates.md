# PR Review Prompt Templates

These templates are filled in by the orchestrator using values from
`<review_dir>/context.json` (produced by `scripts/agint-review-setup`) and from the
scout pass.

The same filled-in prompt is used however the agent runs (see SKILL.md → "How
agents run"): as the task of an `agint-review-<name>` subagent on Claude Code, as the
task of a subagent started by another harness's subagent tool, or, when there is no
subagent tool, as the input the orchestrator works from while it follows the
agent's instruction file itself.

## Pass-by-reference, not by inlining

**The orchestrator passes file paths in prompts; sub-agents `Read` the contents themselves.** Diff text, scout context, reviewer findings, project instruction files, and shared instruction files are all on disk in `<review_dir>` or in the skill's references/ folder. Inlining their contents into prompts would route every byte through the orchestrator's own context, where compression and summarization can distort the canonical text on the way to a downstream agent. Pass-by-reference keeps the orchestrator's context small, makes the disk file the single source of truth, and lets every sub-agent see the exact bytes that were written.

The orchestrator's only remaining text substitutions are short scalars: PR number, title, branch info, author, JIRA key, and absolute paths. Anything that could have been "the file's contents inlined here" should instead be "the path to the file."

---

## Scout Prompt Template

Use this template for the `scout` agent. It runs once, before reviewers, and
produces the shared context block they all receive.

```
You are scouting PR #[number]: "[title]" before specialized reviewers run.

<pr_description>
[PR body — verbatim. Short scalars are still inlined; only file-shaped content is
passed by path.]
</pr_description>

<branch_info>
- head: [headRefName] @ [headRefOid]
- base: [baseRefName]
- author: [author]
- changed files: [count] (+[additions]/-[deletions])
- detected languages: [languages]
</branch_info>

<integration_roots>
[Paste `context.json.integration_roots` verbatim, one root per line as `- <name>`:
the integration roots this PR touches. `(none)` when the list is empty. Record in
your Integrations section whether each one is new or existing.]
</integration_roots>

<jira_key>
[Detected JIRA key, e.g. AGENT-1234. Fetch the issue yourself via the Atlassian MCP.
Omit this block if no key was detected.]
</jira_key>

<diff_path>
[context.json.diff_full_path — absolute path to the full PR diff on disk.]

Read this file to see the unified diff for every changed file in the PR.
</diff_path>

<source_code_access>
- head tree (with PR applied): [head_tree absolute path]
- base tree (without PR):      [base_tree absolute path]

Use `Read`/`Grep`/`Glob` with absolute paths into either tree. The trees are read-only.
Do not read `.claude/`, `.cursor/`, or other agent config files inside the worktrees.
</source_code_access>

Write the scout context document to: [review_dir]/scout-context.md

Follow the section structure defined in your agent instructions. Stay terse and factual.
```

---

## Reviewer Prompt Template

Use this template for each reviewer agent. The scout context replaces the per-agent
re-derivation of intent, JIRA, and tool background — every reviewer reads the same
shared ground from the same file on disk.

```
You are reviewing PR #[number]: "[title]"

<repository>
[context.json.repo_name, e.g. integrations-core or marketplace. The severities you can
use depend on it: see Severity by repository in tenets.md.]
</repository>

<scout_context_path>
[Absolute path to [review_dir]/scout-context.md.]

Read this file first. It is the shared, factual ground produced by the scout pass —
authoritative for intent, surface area, blast radius, tool capabilities, and
pre-existing issues. Do not re-derive these.
</scout_context_path>

<changed_files>
[Filtered list of files matching this agent's patterns — from
context.json.agents_to_run[N].files. Short list, inlined here.]
</changed_files>

<integration_roots>
[Paste `context.json.integration_roots` verbatim, one root per line as `- <name>`:
the integration roots this PR touches. `(none)` when the list is empty.

Informational: whether each one is new or existing is in the scout context's
Integrations section.]
</integration_roots>

<diff_path>
[Absolute path to this agent's filtered diff:
context.json.agents_to_run[N].diff_path.]

Read this file to see the diff for the files you should review.
</diff_path>

<source_code_access>
- head tree (with PR applied): [head_tree absolute path]
- base tree (without PR):      [base_tree absolute path]

Use `Read`/`Grep`/`Glob` with absolute paths into either tree to investigate broader
impact beyond the diff. The trees are read-only. Do not read `.claude/`, `.cursor/`,
or other agent config files inside the worktrees.
</source_code_access>

<instruction_paths>
[Paste `context.json.agents_to_run[N].instruction_paths` verbatim, one entry per
line as `- <label>: <path>`. The setup script has already resolved the bundled
rules (tenets, output contract, comment style), any per-repo overrides under
`.claude/agint-review/`, the AGENTS.md files on the changed paths (conventions only)
the downloaded caller workflows (github-actions on integrations-core only) and the
standard metric allowlist (integrations on integrations-core only), in the right order. Do not Glob; do not re-derive.]

Read each of these before forming findings. The shared instruction files are
mandatory on every run; the project-specific files (when present) take priority
over general guidelines when they conflict. Your agent file may also name reference
files to read depending on what the PR touches: they are in the same `references/`
folder as `tenets.md`.
</instruction_paths>

<findings_path>
[Absolute path to [review_dir]/findings/<agent-name>.md.]

Write your final findings to this file when you're done — `Write` your complete output
there in the format defined in the shared instruction files. The orchestrator does not
capture your return text and re-write it; the file you write is the canonical record
of your review. Returning a brief summary alongside is fine, but the disk file is
authoritative.
</findings_path>

<general_rules>
- Trust the scout context for intent and blast radius. Don't re-derive what's already
  there. Spend your tokens on the work only your agent can do.
</general_rules>

Review this PR according to your instructions and the tenets, and write your findings
in the format defined in the reviewer output contract.
```

---

## Challenger Prompt Template

```
You are challenging the findings from a PR review of PR #[number]: "[title]"

<repository>
[context.json.repo_name, e.g. integrations-core or marketplace. Enforce Severity by
repository in tenets.md for it.]
</repository>

<scout_context_path>
[Absolute path to [review_dir]/scout-context.md. Read this for intent, surface area,
and tool/domain context.]
</scout_context_path>

<diff_path>
[context.json.diff_full_path — absolute path to the full PR diff on disk.]

Read this file to see the unified diff for every changed file.
</diff_path>

<findings_dir>
[Absolute path to [review_dir]/findings/.]

This directory contains one file per reviewer, named `<agent-name>.md`, each holding
that reviewer's full raw findings as written. Read every file in this directory
before issuing verdicts. The agent name is the filename minus `.md` — use it as the
source agent in your verdict report.

Reviewer files present in this run:
[List of "<agent-name>.md" filenames, one per line, derived from
context.json.agents_to_run.]
</findings_dir>

<instruction_paths>
[Paste `context.json.challenger_instruction_paths` verbatim, one entry per line as
`- <label>: <path>`. Setup has already resolved the shared bundled rules (tenets,
output contract, comment style), the project common file (if present), every
per-repo agent file and AGENTS.md file reviewers were given in this run, and the
caller-workflow index when github-actions got one, and the standard metric allowlist
when integrations got it. Do not Glob.]

Read these to know the rules reviewers were operating under. Check every finding
against the tenets and the output contract, and every AGENTS.md citation against the
section it names. Apply the citation_failure_protocol from your own instructions when
you see citations that don't verify.
</instruction_paths>

<report_path>
[Absolute path to [review_dir]/challenger.md.]

Write your full challenger report to this file. Returning a brief verdict-summary
line is fine, but the disk file is authoritative — the orchestrator reads it from
disk during synthesis, not from your return text.
</report_path>

Challenge each finding, write the full challenger report to `<report_path>`, and
return a one-line summary (e.g. `12 kept, 3 demoted, 5 dropped, 1 merged, 2 contested`).
```
