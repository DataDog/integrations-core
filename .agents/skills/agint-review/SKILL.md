---
name: agint-review
description: "Review a Datadog Agent integrations PR (integrations-core, integrations-extras, marketplace, integrations-internal) with specialized agents: the repo's AGENTS.md conventions on every PR, plus integration, security, ddev, GitHub Actions or log pipeline reviewers depending on what it touches. Use when the user wants a code review of a Datadog Agent integrations PR."
argument-hint: "<PR-URL> [aspect1 aspect2 ...] [--round N]"
disable-model-invocation: true
allowed-tools: Glob, Read, Write(.agint-review/*), WebSearch, mcp__atlassian__getJiraIssue
model: sonnet
---

# Review (`agint-review`)

Review a pull request by running a scout pass to gather shared context, then running specialized review agents, challenging their findings, synthesizing the result into a single cohesive review, and posting it to the PR.

This skill runs on Claude Code and on other harnesses that load skills (such as pi). Everything that has to be exact (fetching the PR, choosing agents, worktrees, posting, cleanup) lives in Python scripts that only need Python 3.11+ and `gh`. Nothing in the required path asks the user a question.

## Paths

The scripts are in `scripts/`, next to this `SKILL.md`. Your harness tells you where it loaded this skill from (on Claude Code, the "Base directory for this skill" line; on pi, the "References are relative to <dir>" line at the top of the skill block); the setup script is `<that directory>/scripts/agint-review-setup`. **Never `Glob` for it**: other checkouts and older installs of the skill can hold stale copies, and a Glob can pick one.

You only resolve that one path yourself. The setup script writes every other absolute path the run needs into `context.json`:

- `paths.post_script`, `paths.cleanup_script`: the posting and cleanup scripts
- `paths.prompt_templates`, `paths.output_format`, `paths.comment_style`, `paths.common_agent_instructions`, `paths.tenets`: the references
- `paths.scout_agent`, `paths.challenger_agent`, `agents_to_run[i].agent_file`: each agent's instruction file
- `review_dir`, `head_tree`, `base_tree`, `diff_full_path`, `agents_to_run[i].diff_path`, `agents_to_run[i].instruction_paths`, `challenger_instruction_paths`: this round's files

Use those values verbatim. Never write `${CLAUDE_SKILL_DIR}` or a relative path into an agent's prompt.

## Parameters

- **PR URL** (required) — full GitHub URL (e.g., `https://github.com/DataDog/integrations-core/pull/1234`). A bare PR number is also accepted; the repo is inferred from the current git remote.
- **Aspect filter** (optional) — one or more aspect keywords to restrict which reviewers run. See [Aspect Filter](#aspect-filter) below.
- **`--round N`** (optional) — set the round number, e.g. to redo a round. By default setup uses the next round; don't ask the user which round to run.

The skill's arguments are `$ARGUMENTS` on Claude Code; on pi, they're the text after `/skill:agint-review`, which pi sends as the user's message after the skill block. Below, "the arguments" means either. If the arguments don't contain a PR identifier, ask the user for one before proceeding.

**Slack review coordination.** Every review is posted to GitHub when it finishes, so the Agent Integrations Slack coordinator sees it. The posting script adds the machine-readable marker `<!-- agent-integrations-review-skill:requests=N -->`, where `N` is the number of comments that start with `**Request**`; do not edit or remove it, and keep the `**Request**` label format exactly. If a new commit is pushed to the PR, run the review again against the new head.

**Multi-round reviews.** A PR can be reviewed more than once — typically because the author pushed updates and wants a fresh look. Each round runs as a separate `/agint-review` invocation against its own `round-<N>/` directory. Setup picks the round number: the latest existing round + 1, or 1 for a new PR. Pass `--round N` only to redo a specific round. At the start of every run, setup also deletes the folders of merged or closed PRs under `.agint-review/` and removes worktrees that crashed runs left behind (see Step 1). Each round runs every agent fresh against the updated PR head.

**Parsing the arguments.** Split on whitespace. The PR identifier is the first token that looks like a PR URL or a bare integer. `--round <N>` (consumes the next token as an integer) is recognized exactly as on a command line. Remaining tokens are aspect keywords. Pass the parsed `--round` flag through to the setup script verbatim — do not consume it locally.

## Agents

The setup script in [Step 1](#step-1-setup) picks the agents for this PR and writes the plan to `context.json.agents_to_run`; follow that list, don't re-derive it. It routes PRs like this:

| PR touches | Agents |
|---|---|
| An integration, `datadog_checks_base` or `datadog_checks_dev` | `conventions`, `integrations`, `security` |
| `datadog_checks_downloader` | `conventions`, `security` |
| `ddev/`, `.ddev/` | `conventions`, `ddev` |
| `.github/workflows/`, `.github/actions/` or `.github/chainguard/` | `conventions`, `github-actions` |
| `<integration>/assets/logs/` | `conventions`, `logs` |
| Anything else (`.builders/`, `docs/`, root files) | `conventions` |

- **Scout** (`scout`) — runs first, alone. Reads the PR end-to-end and produces a shared context block (intent, surface area, blast radius, whether each integration is new, product context, description-vs-diff consistency, pre-existing issues). Reviewers consume this so they don't re-derive the same context.
- **Reviewers** — each reviews only the files it matched:
  - `conventions` — every PR. Reviews only against the repository's `AGENTS.md` files as they are on the target branch, even when the PR edits one (setup passes the ones on the changed paths) and cites file and section for each finding. Nothing else in the review restates `AGENTS.md`.
  - `integrations` — integration folders, `datadog_checks_base`, `datadog_checks_dev`: check implementation, metrics, config spec, customer impact and compatibility, persistent cache, tests, dashboards and recommended monitors. Reads extra references under `references/integrations/` by what the PR touches. It doesn't review `assets/logs/`.
  - `security` — the same files, plus `datadog_checks_downloader` (it ships with the Agent and verifies integration wheels), minus `assets/logs/`: untrusted product data, credentials, TLS, commands, parsing, files and queries.
  - `ddev` — `ddev/` and the repo config in `.ddev/`: imports, output, commands, validations, CLI compatibility, repo config, tests (references under `references/ddev/`).
  - `github-actions` — workflows, local actions and octo-sts trust policies. On integrations-core, setup also downloads the workflow files of other repos that call its workflows `@master`.
  - `logs` — log pipelines and their tests under `assets/logs/`, against the Logs Backend review guide read live from Confluence (with a bundled fallback in `references/logs/`), plus the log source in the integration's config and README.
- **Challenger** (`challenger`) — runs after reviewers. Checks every finding against the tenets, the output contract and any `AGENTS.md` section it cites, and issues `keep`/`demote`/`drop`/`merge`/`contest` verdicts. `contest` means the challenger couldn't decide; you arbitrate it during synthesis.

Every reviewer and the challenger get `references/tenets.md` (how to review), `references/common-agent-instructions.md` (the output contract) and `references/comment-style.md` (wording and comment types) in their instruction paths. Files no specialist matches are reviewed by `conventions` only; setup lists them in `context.json.conventions_only_files`. When the target branch has no `AGENTS.md` at all (integrations-extras, marketplace and integrations-internal have none today), setup skips `conventions` and records it in `context.json.skipped_agents`. The `metadata.csv` metric-type rule then goes to `integrations` instead (setup adds `references/integrations/metric-types.md` to its instructions); the other `AGENTS.md` rules don't apply on a repo that has none.

### Aspect Filter

Aspect keywords map to agents and let the user run a subset:

| Keyword | Behavior |
|---------|----------|
| `conventions`, `integrations`, `security`, `ddev`, `github-actions`, `logs` | Run only the named reviewers (when they match the PR's files) |
| `post` | Post the latest round's saved `review.json` (or the round set by `--round N`) without reviewing again, e.g. after a failed post. Runs only setup and Step 7. |
| `all` (default) | Run everything |

Pass aspects to the setup script via `--aspect a,b,c`.

Only a full review is posted. When an aspect filter runs a subset of the reviewers, setup sets `context.json.post` to `false`: the review is saved and shown but not posted, because the Slack coordinator would read a partial review as a complete one.

### How agents run

Each agent is a plain instruction file in the skill's `agents/` folder (paths in `context.json`). Its frontmatter (`tools`) is enforced only on Claude Code; elsewhere, read the body as instructions and apply the frontmatter yourself as described below. Agent files carry no `model:`: you pick each agent's model from [Models per subagent](#models-per-subagent) on every harness. Every agent gets its prompt from `paths.prompt_templates` and writes its output to the file named in that prompt. Pick the first option that your harness supports:

1. **Claude Code:** spawn a subagent with the Agent tool, `subagent_type: agint-review-<name>` (the repo registers each agent file under `.claude/agents/` with that name; bare `scout` or `conventions` fails with "Agent type … not found"). Launch the reviewers with `run_in_background: true`, all in one message, so they run in parallel (foreground Agent calls serialize even when issued together). Set a short `description`, e.g. `"conventions reviewer for PR 23480"`, and pass `model` from [Models per subagent](#models-per-subagent) on every Agent call.
2. **Another harness with a subagent tool** (e.g. pi with `pi-subagents`): start one subagent per agent, and run the reviewers in parallel if the tool supports it. Give each subagent:
   - the agent file's body as its instructions, and the filled-in prompt as its task;
   - the tools listed in the agent file's `tools:` frontmatter, mapped to the harness's names (read, grep, find, ls, write; bash only where the file lists it). Outside Claude Code nothing enforces that list and the worktrees are writable, so tell the subagent it is read-only except for its own output file;
   - write access for its output file;
   - a fresh context, not a fork of this conversation;
   - the model from [Models per subagent](#models-per-subagent).

   When the harness defines subagents by name, use names that can't collide with its built-in agents, e.g. `agint-review-scout`, `agint-review-conventions`: `pi-subagents` ships its own `scout` and `reviewer`, with other prompts (and `reviewer` has no write tool), so a bare name runs the wrong agent.
3. **No subagent tool:** run the agents yourself, one after another, in this session. For each one: `Read` its agent file, follow it as your instructions with the filled-in prompt as your input, `Write` its output file, and only then start the next agent. Keep each agent to its own scope and rules, and don't carry one agent's findings into the next: the challenger is the step that compares them. Order: scout, then each reviewer in `agents_to_run` order, then the challenger.

All three write the same files (`scout-context.md`, `findings/<name>.md`, `challenger.md`), so synthesis and `review.json` are the same whichever option ran.

### Models per subagent

This table is the only place that sets the agents' models, on every harness. Always pass the model from it when you start each agent, including on Claude Code (the Agent tool's `model`, which takes precedence over any agent definition). The agent files have no `model:`, so an agent started without one inherits your own model, which is chosen for orchestrating, not reviewing.

| Agent | Needs | Examples |
|---|---|---|
| `scout`, every reviewer, `challenger` | A frontier reasoning model, at the tier of the examples | Claude Opus (on Claude Code, `model: opus`), GPT-6.2 Sol |

Pick the model at the examples' tier from whatever provider your harness has: not a smaller model, and not a larger, slower or costlier tier above it. If none of the examples is available, take that provider's equivalent of this tier.

---

## Process

**You MUST narrate the work below with short text status updates.** The user sees nothing else while agents run.

Don't announce the plan before setup runs — until then you don't know which reviewers will fire and the list would be guesswork. Run setup first; the moment it returns, read `context.json.agents_to_run` and post one status update laying out the full plan:

```
Starting review — plan:
- Run scout pass
- Reviewer: conventions
- Reviewer: integrations
- Reviewer: security
…(one Reviewer: <name> per entry in context.json.agents_to_run)…
- Run challenger
- Synthesize and post review
```

Use the bare agent name from the registry (e.g. `Reviewer: conventions`, not `Reviewer: agint-review-conventions`).

Post a one-line status update the moment each step finishes — do not batch. When reviewers run in parallel, several updates land in close succession; that's the signal the user wants.

### Step 1: Setup

The setup script parses the PR identifier, fetches the PR via `gh`, validates that the current repo matches the PR's repo, creates worktrees inside `.agint-review/<PR>/round-<N>/`, writes per-agent filtered diffs, detects the JIRA key, applies the aspect filter, selects agents from the registry, and writes a single `context.json` that every later step reads.

The review dir is **always** under a `round-<N>/` subdir. Setup picks `N` itself: the latest existing round + 1 (1 if none), or the latest existing round when the only aspect is `post`. An explicit `--round N` overrides it. Before creating worktrees, setup cleans up `.agint-review/`: it deletes the whole folder of every other PR that `gh` reports as merged or closed, removes head/base worktrees left in open PRs' folders by runs that crashed more than 6 hours ago, removes this PR's older rounds' worktrees, and runs `git worktree prune`. A PR whose state `gh` can't read is left alone, and the folder of the PR being reviewed is never deleted. It prints one summary line.

Invoke it from the repository the PR belongs to, using the path from [Paths](#paths):

    python3 <skill directory>/scripts/agint-review-setup "<PR_ARG>" [--round <N>] [--aspect <comma,separated>]

Pass `--round` only if the user passed it.

The last line of stdout is the absolute path to `context.json`. Read it; from here on, treat its fields as the source of truth. Stderr contains a human-readable summary — show it to the user so they see which agents will run.

If the script exits non-zero, surface the error message and stop. Do not try to recover by re-implementing the setup — fix the underlying issue and re-run.

- **Exit 2 — preflight failure.** The working directory is not in a shape that allows a clean setup (not a git repo, `gh` missing or not authenticated, an in-progress merge/rebase/cherry-pick/revert/bisect). The script's stderr message ends with an explicit "Stop the skill and ask the user…" line. Surface the message verbatim and stop the review — do not attempt to fix the environment yourself.
- **Exit 1 — operational failure.** Something went wrong fetching or interpreting the PR (PR repo doesn't match current repo, no changed files, `gh` API error). Surface the error and stop.

**`post` aspect — post only:** If the only aspect is `post`, setup creates no worktrees and no new round; it returns the latest round's `context.json` after checking that its `review.json` exists and that the round was a full review (a partial run's review is never posted). Skip straight to Step 7 with that round's `review_dir`. Don't review or re-synthesize anything.

If `context.json.agents_to_run` is empty (and you're not in the `post`-only branch above):

- **Partial run** (`context.json.post` is `false`): tell the user no registered agents matched the changed files and stop. Nothing is posted.
- **Full review** (`context.json.post` is `true`), e.g. a PR that only changes root files, scripts or docs on a repo without `AGENTS.md`: tell the user no reviewer covers the PR's files. Skip Steps 2–5 (no scout, reviewers or challenger), then in Step 6 write a clean `review.json` with `"comments": []` and `"uncovered_files"` set to `context.json.uncovered_files`, run the cleanup script, and post it in Step 7 as usual. The posting script says in the fixed body that no reviewer covers the files and lists them; the review is a `COMMENT` with the marker at `requests=0`, so the Slack coordinator still sees that the PR was reviewed.

**Before moving on, announce the plan** (see [Process](#process)).

### Step 2: Scout

Run the scout (see [How agents run](#how-agents-run); its file is `paths.scout_agent`) with the **Scout Prompt Template** from `paths.prompt_templates`, filled from `context.json`. The scout writes its output to `<review_dir>/scout-context.md`.

Wait for it to finish before starting reviewers — they all read its output.

### Step 3: Reviewers

Before starting: confirm your last status update named every reviewer in `context.json.agents_to_run`. If any are missing, post a corrected plan now.

Run each entry in `context.json.agents_to_run` (see [How agents run](#how-agents-run); its file is `agents_to_run[i].agent_file`) with the **Reviewer Prompt Template**. **Pass paths, do not inline file contents.** The orchestrator never substitutes file bytes into a prompt — only short scalars (PR number, title, branch info, paths). Each prompt carries:
- `<scout_context_path>` — absolute path to `<review_dir>/scout-context.md`. The agent reads it.
- `<diff_path>` — `agents_to_run[i].diff_path`. The agent reads it.
- `<changed_files>` — `agents_to_run[i].files`, inlined (it's a short list).
- `<integration_roots>` — paste `context.json.integration_roots` verbatim (the integration roots the PR touches), one root per line as `- <name>`. Use `(none)` when the list is empty.
- `<instruction_paths>` — paste `agents_to_run[i].instruction_paths` verbatim, one entry per line as `- <label>: <path>`. Setup already merged the bundled rules (`tenets.md`, `common-agent-instructions.md`, `comment-style.md`), any per-repo overrides under `.claude/agint-review/`, the `AGENTS.md` files for `conventions` and the downloaded caller workflows for `github-actions`, in the right order. Do not Glob for project rules yourself.
- `<findings_path>` — `<review_dir>/findings/<name>.md` (setup already created `findings/`).

**Each reviewer writes its own findings file**; the orchestrator doesn't rewrite it from returned text. When a reviewer finishes, confirm the file exists. When subagents run in the background, wait for their completion notifications; do not poll.

If a reviewer finished without writing its file, don't message or resume it. Run that one reviewer again from the start with the same prompt. If the second run also leaves no file, `Write` its returned report to the findings path yourself, verbatim, and tell the user you did.

When every reviewer has finished and every findings file exists, go to Step 4.

### Step 4: Challenger

Run the challenger (see [How agents run](#how-agents-run); its file is `paths.challenger_agent`) with the **Challenger Prompt Template** and a `<report_path>` of `<review_dir>/challenger.md`. The challenger writes its full report there; the file it wrote is the canonical record.

The challenger returns a one-line verdict summary (e.g. `12 kept, 3 demoted, 5 dropped, 1 merged, 2 contested`). Show it to the user before continuing.

### Step 5: Synthesize

**Read from disk, not from memory.** Before composing the synthesis, `Read` `<review_dir>/challenger.md` to load the canonical verdicts and `<review_dir>/findings/<agent>.md` for any reviewer whose original wording you need. Do not rely on agent output from earlier turns — by this point the conversation is long, and reconstructing comments from compressed memory is exactly how distortions slip in. The disk files are the source of truth.

Apply challenger verdicts, then merge findings into a single cohesive review. Don't concatenate raw agent outputs.

1. **Filter by verdict.** `keep` as-is. `demote` with reduced severity. `drop` excluded. `merge` fold into the canonical `keep` entry — the canonical finding's body should preserve both its own concrete fix and the angle the merged entry contributed (the challenger's "Merged" table names the angle explicitly). `contest` arbitrate using the diff and your judgment.
2. **Group** by file and line range.
3. **Deduplicate.** Multiple agents flagging the same issue → one comment. The highest severity wins.
4. **Cross-reference.** Combine related findings where they strengthen each other.
5. **Sort out Follow-ups.** A finding about a problem the PR didn't introduce and doesn't make worse is a **Follow-up**, whatever severity the reviewer gave it (check the base tree when in doubt). Follow-ups never count as Requests: they don't make the review `REQUEST_CHANGES` and they aren't in the marker's count.
6. **Apply the severity by repository.** On integrations-extras, marketplace and integrations-internal (`context.json.repo_name`), a **Request** is only for a security issue or something actually broken; anything else is at most a **Suggestion** (see `paths.tenets` › Severity by repository). The challenger already demoted these; don't promote them back.
7. **Apply the severity floor for the PR's size.** Use `context.json.stats` to pick the floor:
   - **Tiny** (< 50 lines changed): drop **Nit**.
   - **Small / medium** (50–500 lines): all severities allowed.
   - **Large** (500–1500 lines): drop **Nit**; demote borderline **Suggestion**s to **Question** unless the recommendation is unambiguous.
   - **Massive** (> 1500 lines): keep only **Request**, high-confidence **Suggestion**, **Question** and **Follow-up**. Everything else suppressed.
8. **Apply the per-file budget.** No file may carry more than **5 comments** in the final review. The rolling-comment merge is **only** triggered when a file exceeds 5 — it is not a default tactic for tidying up. If a file is at or under the cap, leave each finding at its actual anchor (line number, kind, severity) so the author sees one comment per concern. Pre-emptively merging unrelated low-severity findings into a single "anchored here for compactness" rolling comment costs the author signal — they have to mentally split it back into its parts and chase each line. When a file *is* over the cap, merge the lowest-severity ones first ("Several minor style notes at lines 47, 62, 89: …") until you're at the cap, and prefer merging findings that are genuinely the same kind of concern (style, naming, type-shape) rather than a grab-bag.
9. **Write the comments.** Follow the rules in `paths.comment_style` — first person, why before what, specific lines, concrete fixes, no repetition. Start each finding with its type label exactly as written there, followed by a colon and a space (`**Request**: …`; never `**Request:**` or `**Request (blocking)**`). The posting script refuses any other form, because the event and the Slack marker are counted from these labels (`**Request**`, `**Suggestion**`, `**Question**`, `**Nit**`, `**Follow-up**`).

Format per `paths.output_format` and produce both the markdown review and the JSON `comments` array. A clean review (no comments) is valid: `comments` is `[]`.

### Step 6: Save

Display the markdown review in the terminal. Then `Write` the JSON payload to `<review_dir>/review.json` per the schema in `paths.output_format`. Do not use Bash heredocs. The payload carries `pr_number`, `repo`, `commit_sha`, `author`, and `comments`.

Then remove the worktrees right away, before posting and whether or not posting will succeed: nothing needs them after synthesis (`gh-post-review` reads the diff from the GitHub API).

    python3 <paths.cleanup_script> <review_dir>

It removes `head/` and `base/` and runs `git worktree prune`. Every text file stays (`findings/`, `diffs/`, `challenger.md`, `diff.full`, `scout-context.md`, `context.json`, `review.json`), so the user can still ask for the suppressed comments and a failed post can be retried. If it exits non-zero, show its warning and go on.

### Step 7: Post

If `context.json.post` is `false` (a partial run), stop here: tell the user the review was saved to `<review_dir>/review.json` and not posted. Otherwise, post the review right away; don't ask first.

Run exactly the `paths.post_script` path from `context.json`, never a script of the same name found elsewhere (for example inside the PR's worktrees):

    python3 <paths.post_script> <review_dir>/review.json

The script picks the event itself: `REQUEST_CHANGES` when any comment is a **Request**, `COMMENT` otherwise, and always `COMMENT` on your own PR, where GitHub doesn't allow requesting changes. It never approves. A review with no comments is still posted, with "No comments" in the body (or, when `review.json` has `uncovered_files`, a line saying no reviewer covers the PR's files, followed by them). The body is fixed (greeting, count line, comments that couldn't go inline, legend, marker); don't add to it. A commit is posted once per account: if you already posted a review of this commit with the skill, the script prints its URL and exits 0 without posting. Pass `--repost` only when the user asks to post the same commit again. If the script is missing, tell the user and stop — do not post directly via `gh api`.

- **Exit 0:** show the review URL. The review is done.
- **Non-zero exit:** show the error and stop. The script prints the command that posts the saved `review.json` again without reviewing again (`python3 <paths.post_script> <review_dir>/review.json`, or `/agint-review <PR> post` on Claude Code and `/skill:agint-review <PR> post` on pi); pass it on to the user. If it lists bad comment labels, fix exactly those labels in `review.json` and run the same command again. If the error says the PR head changed, tell the user to run a full review again instead.

The review ends here.

---

## Comment Style

The single source of truth is `references/comment-style.md` (`paths.comment_style`). It is appended to every reviewer prompt, used by the challenger when judging findings, and binds the orchestrator during Step 5 (Synthesize). Read it before you write any comments yourself; do not duplicate its rules here or anywhere else.

---

## Rules

- Always require a PR URL (or bare PR number). Never guess or default.
- Show the user the agent plan from the setup summary before running the scout — they should see what's about to happen.
- The setup script handles all `gh`/`git` calls, file selection, and worktree creation. Do not duplicate that logic in the orchestrator.
- Reviewers and the challenger are read-only: each writes only its own output file. When you run an agent's instructions yourself (no subagent tool), the same applies to you while you act as that agent.
- Post only through `paths.post_script`, once, at Step 7. Partial runs (aspect filter) never post.
- A clean review is valid output — say so if all agents reported nothing, and still post it.
- Each round runs every agent fresh. Agents from an earlier run are never resumed.
