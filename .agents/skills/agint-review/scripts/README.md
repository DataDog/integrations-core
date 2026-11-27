# `agint-review` scripts

> **For agents and human maintainers — keep this README in sync with the scripts.**
> If you change a script's CLI surface, observable behavior, output schema, or the way it's invoked from the orchestrator, update the matching section in this README in the same change.
> If you add, remove, or rename a script, update the [Overview](#overview) table, the [Table of contents](#table-of-contents), and add or remove the script's section.
> Pure bug fixes, internal refactors, or changes that don't alter what the script does from the outside do **not** require a README update — this is reference documentation, not a changelog.

This directory holds the executable helpers that back the `agint-review` skill. They exist so the skill body stays small and the model only has to do what models are good at — judgment, synthesis, writing comments — while the deterministic plumbing (parsing PRs, creating worktrees, selecting agents, posting to GitHub) lives in code that runs the same way every time.

All scripts are pure Python 3.11+ (stdlib only, no extra dependencies) and are invoked via `python3 <script-path>` from the orchestrator. The orchestrator finds the setup script next to `SKILL.md` (see [Paths](../SKILL.md#paths)), and the other two through `context.json.paths`, which setup writes (not by `Glob`-ing, which can match stale copies of the skill). Nothing depends on Claude Code: they run the same on any harness that has Python and `gh`.

## Table of contents

- [Overview](#overview)
- [`agint-review-setup`](#agint-review-setup)
  - [What it does](#what-it-does-agint-review-setup)
  - [Inputs and outputs](#inputs-and-outputs-agint-review-setup)
  - [Preflight checks](#preflight-checks)
  - [Helpers worth knowing](#helpers-worth-knowing)
  - [Agent selection](#agent-selection)
  - [Callers in other repos](#callers-in-other-repos)
  - [Integration root detection](#integration-root-detection)
  - [`context.json` schema](#contextjson-schema)
  - [Error handling](#error-handling-agint-review-setup)
- [`agint-review-cleanup`](#agint-review-cleanup)
  - [Sweeping `.agint-review/`](#sweeping-agint-review)
- [`gh-post-review`](#gh-post-review)
  - [What it does](#what-it-does-gh-post-review)
  - [Inputs and outputs](#inputs-and-outputs-gh-post-review)
  - [Comment positioning model](#comment-positioning-model)
  - [Posting flow and fallbacks](#posting-flow-and-fallbacks)
  - [`review.json` input schema](#reviewjson-input-schema)
  - [Body composition](#body-composition)
  - [Error handling](#error-handling-gh-post-review)
- [How the orchestrator uses these scripts](#how-the-orchestrator-uses-these-scripts)
- [Adding a new script](#adding-a-new-script)

---

## Overview

| Script | Stage | Purpose |
|--------|-------|---------|
| [`agint-review-setup`](#agint-review-setup) | Beginning of a review | Parses the PR, creates worktrees, selects which review agents to run, and writes a single `context.json` the orchestrator reads. |
| [`agint-review-cleanup`](#agint-review-cleanup) | Right after synthesis (before posting), and from setup for leftover worktrees | Removes a round's `head`/`base` worktrees and runs `git worktree prune`. Keeps every text file. |
| [`gh-post-review`](#gh-post-review) | End of every review | Takes the synthesized `review.json` and posts the review to GitHub with every comment in a review thread, anchoring off-diff findings on a related changed line. |

The scripts are **side-effect explicit**: they don't `cd`, and they only touch the review directory, its git worktrees, the repo's `.gitignore` (setup) and the GitHub API (setup reads, `gh-post-review` posts). Setup and cleanup are idempotent. If a step fails, they fail loudly with a useful error rather than continuing silently.

---

## `agint-review-setup`

### What it does (`agint-review-setup`)

The orchestrator runs this script first, at [SKILL.md Step 1](../SKILL.md#step-1-setup). `main()` is a linear pipeline; each stage feeds the next and a failure halts it with a clear error:

1. Runs the [preflight checks](#preflight-checks) (exit 2 on failure), then `git worktree prune` to drop records of worktrees whose paths are gone.
2. Parses the PR identifier (URL or bare number) and fetches the PR metadata via `gh`.
3. Verifies the current repo matches the PR's repo (hard fail if not — worktrees would land in the wrong place otherwise).
   Then it [sweeps `.agint-review/`](#sweeping-agint-review) for other PRs' folders: deletes merged/closed PRs' folders, removes leftover worktrees in open PRs' folders, runs `git worktree prune`, and prints one summary line.
4. With `--aspect post` alone, stops here: it returns the latest round's existing `context.json` (after checking that `review.json` exists), with fresh `paths`, so the orchestrator can post the saved review without reviewing again. It refuses (exit 1) when that round was a partial run (`post: false`), and keeps the saved `aspects` and `post`. Otherwise it fetches the changed-files list and the full diff.
5. Picks the round number (see `--round` in `--help`) and runs [`agint-review-cleanup`](#agint-review-cleanup) on this PR's older rounds to remove any worktrees they still have.
6. Fetches the PR head and base branch from the git remote that points at the PR's repository (`origin` unless only another remote does, as in a fork clone whose `gh repo set-default` is the upstream), creates two `git worktree`s at `.agint-review/<PR>/round-<N>/{head,base}` so reviewer agents can read the code as it will look after merge and as it looks today on the base branch, and creates an empty `findings/` dir. A redone round (`--round N`) first deletes everything the earlier run left except the worktrees (`findings/`, `diffs/`, `scout-context.md`, `challenger.md`, `review.json`, `context.json`): the challenger reads every file in `findings/`, and `post` would otherwise publish the earlier run's `review.json`.
7. Adds the review directory base to `.gitignore` if it's not already covered.
8. Detects the [integration roots](#integration-root-detection) from the head and base worktrees (base too, so a PR that deletes a whole integration still gets its reviewers), loads the agent registry, applies the optional aspect filter, and produces a per-agent file list. It also lists the files no agent but `conventions` reviews.
9. Writes a per-agent filtered diff to `<review_dir>/diffs/<agent>.diff` so each reviewer only loads what it needs.
10. Resolves each agent's and the challenger's `instruction_paths`: the bundled tenets, output contract and comment style, the `.claude/agint-review/` overrides, and for `conventions` the `AGENTS.md` files on its changed paths.
11. If `github-actions` is selected on integrations-core, [downloads the callers' workflows](#callers-in-other-repos) from the other repos that call integrations-core workflows `@master` and adds their index to that agent's `instruction_paths` (and to the challenger's). Best-effort: a repo no `gh` account can read is skipped with a warning.
12. Detects an optional JIRA key by regex on the title and branch name.
13. Writes `context.json` (with `post: false` when an aspect filter narrowed the reviewers), prints a summary to stderr and the path to `context.json` on stdout.

Re-running the script on the same round starts that round over: existing worktrees are reused and moved to the current SHAs, the earlier run's outputs are deleted, and `.gitignore` lines are de-duped.

### Inputs and outputs (`agint-review-setup`)

Arguments: run `agint-review-setup --help` or see the script's docstring.

```
stdout (last line):      Absolute path to <review_dir>/context.json
stderr:                  Human-readable progress and summary
filesystem:
  <review_dir>/context.json
  <review_dir>/diff.full
  <review_dir>/diffs/<agent>.diff           (one per selected agent)
  <review_dir>/findings/                    (empty; reviewers write <agent>.md here)
  <review_dir>/head/                        (git worktree at PR head SHA)
  <review_dir>/base/                        (git worktree at base ref)
  <review_dir>/callers/index.md             (only for github-actions on integrations-core)
  <review_dir>/callers/<owner>/<repo>/.github/workflows/*.yml
  <repo_root>/.gitignore                    (appended if not already covering the review dir base)
```

`<review_dir>` is always `<review-dir-base>/<PR>/round-<N>/`, so round-N output never overwrites round-(N-1) output. The other files in a round dir are written by the orchestrator and agents; see the [disk layout](../README.md#disk-layout-under-agint-reviewprround-n).

The split between stdout and stderr is intentional: stdout carries machine-readable output (just the path to `context.json`), and stderr carries the human-readable summary the orchestrator surfaces to the user.

### Preflight checks

Preflight checks run before any network call or filesystem mutation (the agent-file check reads the registry first, which is local). They exist because the rest of the pipeline assumes a clean environment, and a failure deep in `git worktree add` produces confusing error messages compared to a clear "you have a merge in progress" up front. The checks:

- **Inside a git repo** (`git rev-parse --show-toplevel`). If not, the pipeline can't proceed at all; we return immediately so other checks don't add noise.
- **`gh` installed and authenticated** (`which gh` + `gh auth status`). The pipeline relies on `gh` for every PR-related call.
- **The agent instruction files exist.** Setup builds each agent's path from its own location (`scripts/` → skill → `agents/`). A copy of the skill without its `agents/` folder fails here, before any worktree is built.
- **No in-progress git operation** (no `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `BISECT_LOG`, `rebase-merge/`, or `rebase-apply/` in the absolute git dir). `git worktree add` will misbehave or refuse mid-operation.

Stale worktree records (paths no longer on disk) are not a preflight failure: setup runs `git worktree prune` right after the checks pass.

When a check fails, all preflight issues are collected and printed together with explicit "Fix: ..." advice for each, ending with "Stop the skill and ask the user to address the issues above before retrying." The script exits with code **2** to distinguish environmental failures from operational ones (exit 1, see [Error handling](#error-handling-agint-review-setup)).

### Helpers worth knowing

Each helper function has one job. A few worth knowing:

- **`parse_pr_id(token)`** — accepts either `https://github.com/<owner>/<repo>/pull/<N>` or a bare number. URL form yields `(pr_number, repo)`; bare number yields `(pr_number, None)` and lets `gh` infer the repo from the current remote. Backwards-compatible with the original skill while pushing users toward the safer URL form (which makes the repo-mismatch check possible).

- **`fetch_pr_metadata(pr_number, repo)`** — one `gh` call with an explicit `--json` field list. Choosing the field list explicitly keeps the contract stable: if `gh` adds new fields by default, the script doesn't pay for them, and every consumed field is documented at the call site.

- **`split_unified_diff(diff_text)`** — splits a unified diff on `diff --git a/X b/Y` headers, keying blocks by the `b/` (post-image) path. This matches the post-image paths returned by `gh pr diff --name-only` and the way reviewer agents talk about "the file as it will look after merge." Renames produce different `a/` and `b/` paths; we use `b/` because that's where the agent will read the file in the head worktree.

- **`setup_worktrees(...)`** — three deliberate choices:
  1. **Fetches via `pull/<N>/head`** rather than the branch name, so fork PRs (where the head branch isn't on the base remote) work uniformly without branching logic.
  2. **`git worktree add --detach`** — without `--detach`, git tries to create a local branch named after the SHA, which fails on subsequent runs.
  3. **Idempotent** — if a worktree already exists, it is reused, and checked out (`--detach`) at the target SHA if it points elsewhere, so a redo never reads stale source. Cheap re-runs are useful when iterating on the orchestrator.

- **`ensure_gitignore(repo_root, review_dir_base)`** — appends `<review_dir_base>/` to `.gitignore` if not already covered, accepting any of `.agint-review`, `.agint-review/`, `/.agint-review`, `/.agint-review/` as "already there." This replaces the original skill's "please add this to your .gitignore" warning — friction with no payoff.

- **`detect_jira_key(*texts)`** — pattern `\b([A-Z][A-Z0-9]{1,9}-\d+)\b` over the title and branch name. Soft-fail by design: a false match just means the scout's MCP call later returns nothing, and the scout proceeds without JIRA context.

### Agent selection

The registry lives in `references/agent-registry.toml` — TOML rather than JSON so it can carry inline comments explaining the schema. It's parsed via `tomllib` (stdlib in Python 3.11+, no new dependency).

`select_agents(files, registry, aspect_filter, integration_roots)` walks the registry and gives each agent the changed files it matches. An agent matches a file through any of:

| Field | Matches |
|------|------|
| `matches = "all_files"` | Every changed file. Used by `conventions`, which runs on every PR. |
| `matches = "integration_roots"` | Every changed file under a touched [integration root](#integration-root-detection). |
| `globs = [...]` | Files matching a glob (`**` is any number of path components, `*` one). `integrations` and `security` combine it with `integration_roots` to add `datadog_checks_base/**` and `datadog_checks_dev/**`, which `.ddev/config.toml` marks as not integrations. |
| `exclude_globs = [...]` | Optional, same syntax as `globs`. A file matching one is never the agent's, whatever `matches` and `globs` say. `integrations` and `security` exclude `**/assets/logs/**`, which `logs` reviews. |

An agent with no matched file doesn't run. The aspect filter is checked first; if `--aspect` is set and the agent's aspect isn't in the filter (and the user didn't pass `all`), it's skipped before any matching happens.

The result, by what the PR touches:

| PR touches | Agents |
|---|---|
| An integration, `datadog_checks_base` or `datadog_checks_dev` | `conventions`, `integrations`, `security` |
| `datadog_checks_downloader` | `conventions`, `security` |
| `ddev/`, `.ddev/` | `conventions`, `ddev` |
| `.github/workflows/`, `.github/actions/` or `.github/chainguard/` | `conventions`, `github-actions` |
| `<integration>/assets/logs/` | `conventions`, `logs` |
| Anything else (`.builders/`, `docs/`, root files, other packages) | `conventions` |

`conventions_only_files(...)` runs the same matching without `conventions` and returns the files nothing else matched; setup writes them to `context.json` and the summary.

`skip_conventions_without_agents_md(selected, base_tree)` drops `conventions` when the target branch has no `AGENTS.md` at all, root or nested (`git ls-files` in the base tree; integrations-extras, marketplace and integrations-internal have none today). Any `AGENTS.md` keeps it, even one off the changed paths, since `conventions` also reads nested files whose subject the PR uses, so a full agent run isn't spent writing an empty findings file. The skipped agent and the reason go to `context.json.skipped_agents` and the summary.

`add_rules_conventions_would_own(...)` then adds `references/integrations/metric-types.md` (the `metadata.csv` metric-type rule, which on integrations-core lives in the root `AGENTS.md`) to the `integrations` agent's and the challenger's `instruction_paths`, only when `conventions` was skipped that way, so the rule is checked once on every repo.

`agents_md_on_paths(base_tree, files)` lists the `AGENTS.md` files between each of `conventions`' files and the repo root, root first. Every one is read from the base tree (the target branch's tip), even one the PR edits, adds, renames or deletes: the target branch's rules are the ones in force, a branch that is behind may carry an outdated copy, and a PR doesn't change the rules its own review applies. They go into `conventions`' `instruction_paths` (and the challenger's, to check its citations), labelled "(target branch)".

### Callers in other repos

Other repos call integrations-core workflows, and only the callers `@master` change when integrations-core does. `github-actions` can't search other orgs, so when it runs on integrations-core, `fetch_master_callers` downloads, from `DataDog/integrations-extras`, `DataDog/marketplace` and `ddoghq/integrations-internal`, every `.github/workflows/` file with a `uses:` of an integrations-core workflow or action at `@master`, to `<review_dir>/callers/<owner>/<repo>/`. It writes `callers/index.md`: per repo, the account used, the files and their calling lines, or why it was skipped. A file that fails to download is listed under "Missing" with a warning, and a repo is only reported as having no callers when every one of its files was read.

DataDog and ddoghq repos need different GitHub accounts, and reading a repo with the wrong one returns 404, not a permission error. So `gh_tokens()` collects a token in `GH_TOKEN`/`GITHUB_TOKEN` if set, then one per account logged in to github.com (`gh auth status --json hosts`, `gh auth token --user <login>`, run with those variables unset), and each repo is read with the first token that can list its workflows. Each `gh` call gets its token through its own environment; the active account is never switched. A repo no token can read (typically `ddoghq/integrations-internal` without a ddoghq account) is skipped with a warning, and the index says so.

### Integration root detection

The single most subtle piece of logic in the script. `find_integration_roots_in_tree(head_tree)` reads ground truth from the worktree because path-shape heuristics aren't reliable across the integration repos.

The integrations-core repo uses an **inverted convention**: every top-level directory is an integration **by default**, unless explicitly listed `false` in `[overrides.is-integration]` of `.ddev/config.toml`. Excerpt:

```toml
[overrides.is-integration]
datadog_checks_base = false
datadog_checks_dependency_provider = false
datadog_checks_dev = false
datadog_checks_downloader = false
datadog_checks_tests_helper = false
ddev = false
docs = false
trace-captures = false
__pycache__ = false
```

This is how new integrations like `krakend` and `lustre` work without a `manifest.json` — they're integrations because they're not in the denylist.

Other repos (integrations-extras, marketplace, integrations-internal) don't have that section. For those, the script falls back to the older convention: an integration is any directory that contains a `manifest.json` at its top level.

The function:

```python
def find_integration_roots_in_tree(head_tree):
    config_path = head_tree / ".ddev" / "config.toml"
    excluded = None  # None ⇒ denylist absent; set ⇒ denylist present

    if config_path.exists():
        try:
            import tomllib
            data = tomllib.loads(config_path.read_text())
            section = data.get("overrides", {}).get("is-integration")
            if isinstance(section, dict):
                excluded = {k for k, v in section.items() if v is False}
        except Exception as e:
            log(f"warning: could not parse {config_path} ({e})")

    if excluded is not None:
        # Modern model: every non-hidden, non-excluded top-level dir
        return {p.name for p in head_tree.iterdir()
                if p.is_dir() and not p.name.startswith(".") and p.name not in excluded}

    # Fallback: manifest.json convention
    return {p.parent.name for p in head_tree.glob("*/manifest.json")}
```

Three properties this design buys:

1. **No false negatives for new integrations.** `krakend` works because the denylist doesn't exclude it.
2. **No false positives for framework directories.** `datadog_checks_base/`, `datadog_checks_dev/`, etc. are all in the denylist and stay out of the integration-reviewer's domain.
3. **No false negatives for tests-only PRs.** Once we know `kafka/` is an integration root, *any* file under `kafka/` (including tests, READMEs, fixtures) routes to `integrations`. The integration reviewer is the agent that knows how integration tests should be structured, so this routing is what we want.

The roots the PR touches flow through `select_agents` via the `integration_roots` argument and are also surfaced in `context.json`; the scout records whether each is new.

### `context.json` schema

This is the contract between the script and everything downstream.

```json
{
  "pr_number": 1234,
  "repo": "DataDog/integrations-core",
  "repo_name": "integrations-core",
  "title": "...",
  "description": "...",
  "author": "username",
  "branch": {
    "head": "feature-branch",
    "base": "master",
    "head_sha": "abc123..."
  },
  "stats": {
    "additions": 120,
    "deletions": 45,
    "changed_files": 6
  },
  "is_cross_repository": false,

  "review_dir":     "/abs/path/.agint-review/1234/round-1",
  "head_tree":      "/abs/path/.agint-review/1234/round-1/head",
  "base_tree":      "/abs/path/.agint-review/1234/round-1/base",

  "languages": ["python"],
  "integration_roots": ["krakend"],
  "conventions_only_files": [],
  "skipped_agents": [],
  "uncovered_files": [],

  "files": ["krakend/datadog_checks/krakend/check.py", "krakend/tests/test_krakend.py"],
  "agents_to_run": [
    {
      "name": "conventions",
      "aspect": "conventions",
      "files": [...],
      "agent_file": "/abs/path/skill/agents/conventions.md",
      "diff_path": "/abs/path/.agint-review/1234/round-1/diffs/conventions.diff",
      "instruction_paths": [
        {"label": "Review tenets (how every agent reviews)", "path": "/abs/path/skill/references/tenets.md"},
        {"label": "Reviewer output contract",                "path": "/abs/path/skill/references/common-agent-instructions.md"},
        {"label": "Comment style and comment types",         "path": "/abs/path/skill/references/comment-style.md"},
        {"label": "Project common (applies to all agents)",  "path": "/abs/path/repo/.claude/agint-review/common.md"},
        {"label": "Project agent-specific",                  "path": "/abs/path/repo/.claude/agint-review/conventions.md"},
        {"label": "AGENTS.md on the changed paths: AGENTS.md (target branch)", "path": "/abs/path/.agint-review/1234/round-1/base/AGENTS.md"}
      ]
    }
  ],
  "challenger_instruction_paths": [
    {"label": "Review tenets (how every agent reviews)",       "path": "/abs/path/skill/references/tenets.md"},
    {"label": "Reviewer output contract",                      "path": "/abs/path/skill/references/common-agent-instructions.md"},
    {"label": "Comment style and comment types",               "path": "/abs/path/skill/references/comment-style.md"},
    {"label": "Project common (applies to all agents)",        "path": "/abs/path/repo/.claude/agint-review/common.md"},
    {"label": "Reviewer rules (conventions: conventions.md)",  "path": "/abs/path/repo/.claude/agint-review/conventions.md"},
    {"label": "AGENTS.md on the changed paths: AGENTS.md (target branch)", "path": "/abs/path/.agint-review/1234/round-1/base/AGENTS.md"}
  ],

  "jira_key": "AGENT-1234",
  "aspects": [],
  "diff_full_path": "/abs/path/.agint-review/1234/round-1/diff.full",
  "gitignore_appended": false,
  "round": 1,
  "post": true,

  "paths": {
    "skill_dir":                 "/abs/path/skill",
    "setup_script":              "/abs/path/skill/scripts/agint-review-setup",
    "post_script":               "/abs/path/skill/scripts/gh-post-review",
    "cleanup_script":            "/abs/path/skill/scripts/agint-review-cleanup",
    "prompt_templates":          "/abs/path/skill/references/prompt-templates.md",
    "output_format":             "/abs/path/skill/references/output-format.md",
    "comment_style":             "/abs/path/skill/references/comment-style.md",
    "common_agent_instructions": "/abs/path/skill/references/common-agent-instructions.md",
    "tenets":                    "/abs/path/skill/references/tenets.md",
    "scout_agent":               "/abs/path/skill/agents/scout.md",
    "challenger_agent":          "/abs/path/skill/agents/challenger.md"
  }
}
```

A few things worth noting about the schema:

- **All paths are absolute.** The orchestrator may run commands from any cwd. Relative paths would be ambiguous; we trade portability across machines (irrelevant — this file isn't committed) for clarity.
- **`agents_to_run` is the orchestrator's plan.** It iterates this array directly. There's no second decision to make — selection is closed before the orchestrator sees anything.
- **Empty arrays, not absent keys.** When there's no JIRA, no aspects, no conventions-only files, the script emits `null` or `[]` rather than omitting the keys. Consumers can iterate without optional-chaining.
- **Both file index and content paths.** Either could be derived from the other but having both is convenient — the scout wants `files` inline, reviewers want `diff_path`.
- **`repo_name`** is the repo without its owner (`integrations-core`, `marketplace`…), the form the tenets' Severity by repository section uses; it stays the same for a fork or an org move. It goes into the reviewer and challenger prompts.
- **`integration_roots`** lists the integration roots the PR touches. The scout reads it to record which are new, and it answers "why did the integrations reviewer fire?" concretely.
- **`conventions_only_files`** lists the changed files that only `conventions` reviews, so a gap in coverage is visible.
- **`uncovered_files`** lists the changed files that no agent in the plan reviews. When `agents_to_run` is empty on a full review, the orchestrator copies it into `review.json`, so the posted clean review says why it's empty.
- **`skipped_agents`** lists agents that matched but were skipped, with the reason: today only `conventions`, when the target branch has no `AGENTS.md`.
- **`instruction_paths` is fully resolved.** Setup merges bundled rules (`tenets.md`, `common-agent-instructions.md`, `comment-style.md`, always first) with per-repo overrides under `.claude/agint-review/`, plus the `AGENTS.md` files for `conventions` and the callers' index for `github-actions`, and emits one labelled list per agent. The orchestrator pastes the list verbatim into the reviewer's `<instruction_paths>` block — no Glob, no fan-out logic in the prompt. `challenger_instruction_paths` is the union of everything reviewers in this run were given, so the challenger can validate citations against the same set.
- **`paths` and `agent_file` replace harness path substitution.** They're resolved from the script's own location (`scripts/` → skill → `agents/`), so `SKILL.md` needs no `${CLAUDE_SKILL_DIR}` injection and works on harnesses that don't support it. `agent_file` is what a harness without registered subagents reads to run that agent itself.
- **`post`** is `false` when an aspect filter ran only some reviewers. The orchestrator saves a partial review but doesn't post it, because the Slack coordinator would read it as a complete review.
- **`round`** is the round setup picked (or the explicit `--round`). It controls the `round-<N>/` segment of `review_dir`, so every other path in the JSON is rooted under it. It does not affect which agents are selected, which files are diffed, or what the worktrees look like.

### Error handling (`agint-review-setup`)

The script distinguishes **environmental** failures (the workspace can't host a clean review) from **operational** ones (something specific to this PR went wrong) using exit codes:

- **Exit 2 — preflight failure.** See [Preflight checks](#preflight-checks). The user is expected to fix their environment before retrying.
- **Exit 1 — operational failure.** Fast fail with explicit error messages on:
  - **Unrecognized PR identifier** — neither URL-shaped nor a bare number.
  - **`gh` command failure** — bubbled up with stderr included.
  - **Repo mismatch** — current repo's `nameWithOwner` doesn't match the PR's repo. Halts before any worktree is created.
  - **No changed files in PR** — empty diff is treated as a setup error rather than a degenerate review.

Soft failures (continue with reduced functionality):

- **`.ddev/config.toml` parse error** — falls back to the `manifest.json` convention with a stderr warning.
- **JIRA key not found** — `jira_key` is `null` in `context.json`; the scout proceeds without JIRA context.
- **Agent selection produces an empty list** — `agents_to_run` is `[]`. On a full review the orchestrator posts a clean review listing `uncovered_files`; on a partial run it stops without posting (see [SKILL.md Step 1](../SKILL.md#step-1-setup)).
- **Older-round cleanup or `git worktree prune` fails** — warning on stderr; setup continues.
- **A caller repo can't be read with any `gh` account** — it's skipped with a warning, noted in `callers/index.md`, and `github-actions` runs without it.

---

## `agint-review-cleanup`

```
Usage:
  agint-review-cleanup <review_dir> [--review-dir-base NAME]
```

Removes the `head` and `base` worktrees of one round dir with `git worktree remove --force` (falling back to deleting the directory if git doesn't know it), then runs `git worktree prune`. Every text file stays: `findings/`, `diffs/`, `challenger.md`, `diff.full`, `callers/`, `scout-context.md`, `context.json` and `review.json` are small, and keeping them lets the user see suppressed comments and retry a failed post. Worktrees are what take the space (a full integrations-core checkout each).

- Refuses (exit 2) any path not strictly inside a directory named `NAME` (default `.agint-review`), after resolving `..` and symlinks.
- Idempotent: a missing dir, or a round with no worktrees, exits 0.
- Exit 1 if something could not be removed (warning on stderr). The orchestrator shows it and moves on.

The orchestrator runs it right after synthesis, before posting ([SKILL.md Step 6](../SKILL.md#step-6-save)), so a failed or interrupted post never leaves worktrees behind; `gh-post-review` reads the diff from the GitHub API, not from the worktrees. `agint-review-setup` runs it on this PR's older rounds and on [leftover worktrees](#sweeping-agint-review) in other PRs' folders.

### Sweeping `.agint-review/`

At the start of every run, after the repo check, `sweep_review_base()` in `agint-review-setup` looks at every other PR's folder (`.agint-review/<number>/`) and asks `gh pr view --json state` for its state, eight lookups at a time:

- **MERGED or CLOSED:** removes its rounds' worktrees, then deletes the whole folder.
- **OPEN:** keeps the folder and its text files, and removes head/base worktrees in rounds untouched for 6 hours (`LEFTOVER_WORKTREE_MIN_AGE_S`). Younger worktrees may belong to a review another session is running in the same clone.
- **Unknown** (network, auth, 404, timeout): keeps the folder untouched. Nothing is deleted on an unknown state.

The folder of the PR being reviewed is never touched; non-numeric folders are ignored; and nothing is deleted unless it resolves strictly inside `.agint-review/` (a symlinked PR folder pointing elsewhere is refused). Setup then runs `git worktree prune` and prints one line, e.g. `Cleaned up 12 folders for merged/closed PRs, 3 leftover worktrees.`

---

## `gh-post-review`

### What it does (`gh-post-review`)

At the end of every review ([SKILL.md Step 7](../SKILL.md#step-7-post)), the orchestrator runs this script with the synthesized `review.json`. It first refuses to post if the PR's head SHA no longer matches `review.json`'s `commit_sha`, then posts a single GitHub PR review (one timeline entry, not N separate comments) with every comment in a review thread the author can reply to and resolve: at its line, at the file level, or at its `anchor` when the finding is outside the diff (see [Comment positioning model](#comment-positioning-model)). It never abandons the user's content — when GitHub refuses a thread, or everything else fails, the comments go into the review body so they're visible at least somewhere.

The event is picked from the comments: `REQUEST_CHANGES` when any comment body has a line starting with `**Request**`, `COMMENT` otherwise. Follow-ups and every other type never block. The script never sends `APPROVE`. On the reviewer's own PR (the `gh` account is the PR author) it always sends `COMMENT`, because GitHub rejects `REQUEST_CHANGES` from a PR's author; the marker still carries the Request count. If `gh api user` fails, so the script can't tell, a `REQUEST_CHANGES` that GitHub rejects with its "own pull request" error is retried once as `COMMENT`, in the same tier.

Labels are checked before anything is posted, because the event and the marker are both counted from them. Every comment must start with an exact label followed by ": " (`**Request**: `, `**Suggestion**: `, `**Question**: `, `**Nit**: `, `**Follow-up**: `), and no line may start with a near-miss (`**Request:**`, `**Request (blocking)**`, `**request**:`, `**Follow up**:`). Otherwise a misspelled Request would post as `COMMENT` with `requests=0`, and neither GitHub nor the Slack coordinator would see it as blocking. Problems are listed and the script exits 1 without posting.

A commit is posted once per account. Before posting, the script lists the PR's reviews; if one written by the posting `gh` account carries the marker and has `commit_id` equal to `review.json`'s `commit_sha`, it prints that review's URL and exits 0. Reviews by anyone else never count, so a teammate's run on the same commit doesn't stop yours. `--repost` skips this check. If the reviews or the account can't be read, the script warns and posts. A review with no comments is still posted, so the author and the Slack coordinator can see it ran.

Every successfully submitted review includes the invisible HTML marker `<!-- agent-integrations-review-skill:requests=N -->` in its top-level body, where `N` is the number of `**Request**` findings (lines starting with `**Request**`) in the posted comments. This is a machine-readable contract with the Agent Integrations Slack review coordinator; it lets that coordinator identify a review posted by this skill, and whether blocking findings remain, without inspecting inline comments. It is present even for clean reviews and body-only fallbacks.

### Inputs and outputs (`gh-post-review`)

Arguments: the path to `review.json`, plus `--repost` to post a commit that already has a review from the skill. The event and the body aren't configurable (see [Body composition](#body-composition)).

```
stdout:   Progress messages and the resulting review URL on success.
stderr:   Warnings on retries; final error on failure.
network:  GET user (own-PR check), repos/<repo>/pulls/<N> (head SHA),
          .../reviews (already posted? pending review left behind?) and
          .../files (diff lines);
          with file-level threads: POST .../reviews (pending), one GraphQL
          addPullRequestReviewThread per thread, POST .../reviews/<id>/events,
          and DELETE/GET .../reviews/<id> if the submit fails;
          then, if needed, up to four POST calls to .../reviews (two tiers,
          each retried once as COMMENT on an own-PR rejection).
exit:     0 on a successful post or when the commit was already posted;
          1 otherwise.
```

### Comment positioning model

Every comment becomes a review thread. GitHub accepts threads only on files the PR changes, either at a line in the diff on the comment's side (RIGHT for additions and context lines, LEFT for deletions and context lines) or at the file level. A file the PR doesn't touch takes no review comment at all.

A comment's `path`, `line` (and optional `start_line`) are its real target. `0` is a sentinel meaning "a general observation about the file, not tied to any line". `place_comment(comment, diff_lines)` decides where it goes:

| Target | Posted as |
|---|---|
| `line > 0`, within `SNAP_MAX_DISTANCE` (5) lines of a diff line on its side | Line thread at that diff line |
| `line == 0`, file in the diff | File-level thread on the file |
| Anything else, with an `anchor` in the diff | At the anchor: a line thread snapped the same way, or a file-level thread for `anchor.line == 0` |
| File in the diff, no usable anchor | Line thread at the nearest changed line on its side, however far |
| File outside the diff, no usable anchor | File-level thread on the changed file sharing the most leading directories with it (`related_diff_file`) |
| No file of the PR known (the diff fetch failed) | Review body |

The snap within 5 lines silently corrects off-by-one line numbers. In the other re-anchored cases, `target_reference` puts a line at the top of the body naming the real target, linked at `commit_sha`: _About [`path` L228-L256](https://github.com/OWNER/REPO/blob/SHA/path#L228-L256), which this PR doesn't change._ (or _outside the lines this PR changes._ for a file in the diff). LEFT targets aren't linked, since the link shows the head. The label check runs on the bodies as written in `review.json`, so the reference line doesn't affect it. A comment posted on another line than its own, re-anchored or snapped, has its ` ```suggestion ` blocks turned into plain code blocks: GitHub applies a suggestion at the thread's line, so accepting it would overwrite that line instead of the one it was written for. An anchor that isn't in the diff prints a warning and falls through to the script's own choice. The orchestrator is the one that knows which changed line is related, so `output-format.md` asks it to set `anchor` on every off-diff finding; the fallbacks are a guess.

`prepare_comments(raw_comments, diff_lines, repo, commit_sha)` returns the line threads (`{path, line, side, body}` for the create-review payload), the file-level threads, and the comments only the body can carry.

`get_diff_lines(repo, pr_number)` fetches the per-file patches via `gh api repos/.../pulls/<N>/files` and parses each patch with `_parse_patch_lines` to extract the line numbers on each side: RIGHT (additions and context lines, by new-file number) and LEFT (deletions and context lines, by old-file number). The result is `{filename: {"RIGHT": [...], "LEFT": [...]}}`. On any fetch failure, an empty dict is returned: with no known files in the diff, every comment goes into the body and the review still posts — never blocking on a sub-step.

### Posting flow and fallbacks

`POST /pulls/<N>/reviews` only takes line comments: its `comments[]` items have no `subject_type` (that field exists on the standalone `POST /pulls/<N>/comments`, which publishes each comment on its own, outside any review). Sending it fails the whole batch with `Field is not defined on DraftPullRequestReviewThread`. File-level threads are added through GraphQL instead, which needs the review to exist as pending first:

```
File-level threads (only when the review has any):
  create the review pending (POST /reviews with the line threads and no event)
  → addPullRequestReviewThread(subjectType: FILE) per thread, on that review's node id
  → submit (POST /reviews/<id>/events with the event and the body)
   ↓ (if the pending review can't be created, or the submit fails and it is deleted)
Tier 1: one create-review call with the line threads; file-level comments in the body
   ↓ (if GitHub rejects)
Tier 2: a body-only review with every comment as text
```

- A file-level thread GitHub rejects is listed in the submitted body; the rest of the review still posts.
- The pending review is created with the body `<!-- agint-review-pending -->`, which the submitted body replaces. Before posting, and when creating it fails (GitHub may have created it and lost the reply), `discard_own_pending_review` deletes any pending review of the poster's that carries it. GitHub allows one pending review per user per PR, so one left behind would make every later post fail. The poster's own draft never carries the marker and is never touched.
- When the submit fails, the pending review is deleted and Tier 1 runs. If it can't be deleted, the script reads it back: a review GitHub shows as submitted counts as posted (only the response was lost). One still pending stops the script (exit 1) with its id, since GitHub allows one pending review per user per PR and every later post would fail.
- **Tier 1** is today's single call, used directly when there are no file-level threads.
- **Tier 2** doesn't post any threads. Every comment is listed as text in the body, separated by `---`.

GitHub refuses any new review, pending or not, while the posting account has its own pending review on the PR ("User can only have one pending review per pull request"): every tier then fails and the script prints GitHub's error and the retry command.

The script never gives up silently. Once posting starts, the only failures that exit non-zero are "both tiers were rejected by the API," which would mean something fundamental is wrong (missing PR, revoked token, a pending review of the poster's own, SHA moved between the pre-flight check and the post, etc.), and a pending review left behind. The pre-posting checks are listed under [Error handling](#error-handling-gh-post-review).

Every path uses the same event (`REQUEST_CHANGES` or `COMMENT`, from the Request count), retried once as `COMMENT` on an own-PR rejection, and the same count line and marker.

### `review.json` input schema

This is what the orchestrator writes after synthesis (defined in `references/output-format.md`):

```json
{
  "pr_number": 1234,
  "repo": "DataDog/integrations-core",
  "commit_sha": "abc123...",
  "author": "pr-author-username",
  "comments": [
    {
      "path": "krakend/datadog_checks/krakend/check.py",
      "line": 42,
      "side": "RIGHT",
      "body": "**Request**: Missing None check before dict access..."
    },
    {
      "path": "krakend/manifest.json",
      "line": 0,
      "body": "**Suggestion**: file-level note about the manifest..."
    },
    {
      "path": "krakend/datadog_checks/krakend/config_models/defaults.py",
      "start_line": 20,
      "line": 24,
      "side": "RIGHT",
      "anchor": {"path": "krakend/datadog_checks/krakend/check.py", "line": 57, "side": "RIGHT"},
      "body": "**Question**: finding about a file this PR doesn't change..."
    }
  ],
  "uncovered_files": []
}
```

- `path` — the file the finding is about (relative, no leading slash), as it appears in the diff when the PR changes it.
- `line` — integer; `0` means file-level comment; anything else is a 1-based line number (will be snapped).
- `start_line` — optional, `1 <= start_line <= line`; the start of the range, used only in the reference line of a re-anchored comment.
- `side` — `"RIGHT"` for new/changed code (default), `"LEFT"` for deletions; omitted when `line == 0`.
- `anchor` — optional `{path, line, side}`: where to post when the target isn't in the diff (`line: 0` for a file-level thread). See [Comment positioning model](#comment-positioning-model).
- `body` — the comment body. The orchestrator already prefixes the type (`**Request**`, `**Suggestion**`, `**Question**`, `**Nit**`, `**Follow-up**`); the script counts these labels and does not modify the body.

`comments` may be empty: that's a clean review, posted with "No comments".

`uncovered_files` (optional, a list of paths) is set only when setup found no reviewer for the PR's files on a full review; it comes from `context.json.uncovered_files`. With it and no comments, the body says "No comments: no reviewer covers the files this PR changes." and lists the first `UNCOVERED_FILES_SHOWN` (5) files, then "… and N more". Anything but a list of strings is rejected (exit 1).

`commit_id` in the GitHub payload comes from `commit_sha`. `body` is composed by `compose_body()` — see [Body composition](#body-composition) below.

### Body composition

`compose_body(author, comments, unattached, unattached_note, uncovered_files, own_pr)` builds the body, top to bottom:

1. `REVIEW_BODY_HEADER`: "Hi @author, this review was generated automatically. Feel free to discuss any comment you disagree with." On the poster's own PR (the `gh` account is the PR author), `OWN_PR_REVIEW_BODY_HEADER` instead: "Automated review by the [`agint-review`](…) skill. Feel free to discuss any comment you disagree with." When the account can't be read, the greeting is used.
2. The count line from `count_line(comments)`, e.g. "2 Requests block merging · 4 Suggestions · 1 Question", or "No comments". When there are no comments and `uncovered_files` is set, "No comments: no reviewer covers the files this PR changes." and the capped file list instead. A body that combines several findings counts each label; a comment with no recognized label counts as "other".
3. The comments that couldn't be attached to the diff (rejected threads and, in Tier 1, file-level comments; every comment in Tier 2), between horizontal rules. Omitted when there are none.
4. `REVIEW_BODY_LEGEND`: the collapsed legend for request, suggestion, question, nit and follow-up.
5. `MARKER` (`<!-- agent-integrations-review-skill:requests=N -->`), once, last, so it does not alter rendered Markdown.

`comments` is every comment in the review, inline or not, so the count line and the marker cover all of them. A comment body that contains the reserved marker prefix is rejected (exit 1) rather than risking a duplicated contract marker.

### Error handling (`gh-post-review`)

Hard fails (exit 1), all before anything is posted except the last:

- **`review.json` not found.**
- **`gh` not installed** — checked via `which gh`.
- **A comment has a missing or malformed type label** (see [What it does](#what-it-does-gh-post-review)), or a `line`, `start_line` or `anchor` of the wrong shape; the problems are listed.
- **A comment body contains the reserved marker.**
- **PR head SHA moved** since the review was generated — regenerate the review against the current head.
- **A pending review left on the PR** — one the script created (after a failed submit, a lost reply or an interrupted run) could not be deleted; the user discards it on GitHub.
- **Both tiers rejected by the GitHub API** — the final tier prints the API stderr, then the command that posts the saved `review.json` again without reviewing again (`python3 <this script> <review.json>`, or `/agint-review <PR> post` on Claude Code and `/skill:agint-review <PR> post` on pi).

Soft fails (continue with reduced fidelity):

- **Diff fetch fails** — `get_diff_lines` returns `{}`; with no files known to be in the diff, every comment goes into the body and the review posts as body-only.
- **An `anchor` not in the diff** — warning; the script picks the anchor itself.
- **A file-level thread rejected** — listed in the submitted body.
- **File-level flow fails** (pending review not created, or submit failed and deleted) — Tier 1 posts with the file-level comments in the body.
- **Own-PR rejection** — `REQUEST_CHANGES` rejected because the poster is the author: retried as `COMMENT`.
- **Reviews can't be listed** — the "already posted" check is skipped with a warning.
- **Tier 1 rejected** — Tier 2 retries body-only with every comment inlined as text; warning logged.

---

## How the orchestrator uses these scripts

`SKILL.md` tells the orchestrator where the setup script is (in `scripts/`, next to `SKILL.md`; see [Paths](../SKILL.md#paths)); setup then writes the other scripts' absolute paths into `context.json.paths`, so the orchestrator never `Glob`s for them. The invocations are documented where they run: setup in [SKILL.md Step 1](../SKILL.md#step-1-setup), cleanup in [SKILL.md Step 6](../SKILL.md#step-6-save) and posting in [SKILL.md Step 7](../SKILL.md#step-7-post).

### Why scripts and not skill prose

Every action in these scripts used to live in the skill body as natural-language instructions. The model was paying tokens to re-derive deterministic logic on every run, sometimes with subtle drift (slightly different URL regex, different selection rules). Moving the logic into scripts:

- Shrinks the skill body.
- Makes behavior reproducible across runs and across models.
- Lets us unit-test the logic (the helper functions are pure and importable).
- Frees the model to spend its context on judgment, synthesis, and writing comments — which is what we actually want it doing.

---

## Adding a new script

If you add another helper here:

1. Make it executable, shebang `#!/usr/bin/env python3`, stdlib only.
2. Document its CLI in a top-of-file docstring. Include a short *Maintainers* note at the end of the docstring pointing back to this README, mirroring the pattern used by `agint-review-setup` and `gh-post-review`. That keeps the read-on-touch reminder in place for future editors.
3. Add an entry to the [Overview](#overview) table above and a section for the script in this README following the same shape: *What it does → Inputs/outputs → Walkthrough → Schemas → Error handling*. Disambiguate any duplicate subheadings (e.g. "What it does") by appending the script name in backticks so GitHub's anchor algorithm produces unique IDs.
4. Update the [TOC](#table-of-contents) to link to the new section.
5. Add its absolute path to `skill_paths()` in `agint-review-setup`, so it lands in `context.json.paths`, and reference it from `SKILL.md` as `paths.<name>`. Don't hardcode absolute paths and don't `Glob` for it.
