---
name: togo-prd
description: >-
  Interviews an integration engineer and writes a Togo PRD: the product
  requirements document a Togo flow (ddev meta ai) builds a Datadog Agent
  integration from. Researches the product and any given lab, endpoint, or API
  schema first, asks only the decisions research cannot settle, writes a draft
  file the engineer can edit, and explains how to run the flow. Use when asked
  to write, draft, finish, or review a PRD for Togo or ddev meta ai.
---

# Togo PRD

This skill produces one file: a PRD that a Togo flow (`ddev meta ai`) uses to build a Datadog Agent
integration for a product. Everything else (research, the interview, the review rounds) serves that
document: the goal is a PRD the flow can build from, not the interview itself. It ends with a
hand-off in the chat on how to run the flow.

A Togo PRD is the document a product manager would give engineers, with a bit more context on what
to build: what users need to see and alert on, the setup the customer provides, and a few design
choices. A Togo flow includes it in its prompts as the intended scope; what it leaves open, the flow
guesses or stops on. It is not a prompt: it holds no implementation details and no rules for agents,
because the flow prompts own the engineering, testing, and documentation rules. It covers only the
integration (no monitors, dashboards, or other assets).

Research first, and decide what the evidence supports. When the docs, the requirements source, or
the evidence settle a decision, take it and record it with its source in the assumptions list (step
7). Ask the caller when there is no clear evidence or when several answers are valid. The caller has
the last word on every decision: they review the assumptions with the draft. Even in a mode where
you would usually proceed without asking, ask the open decisions and wait for the reply.

## Inputs

- **Integration name** (required), for example `Temporal`. Ask for it if it is missing.
- **Requirements source** (optional): any file or URL you can read, such as a product brief, a
  ticket, or an RFC. It is the caller's voice.
- **Evidence** (optional): a running lab (a Docker Compose project or container), an endpoint URL,
  or an API schema (OpenAPI, WSDL, GraphQL schema). Evidence corrects facts; it never adds scope.

An existing PRD draft is a requirements source. If the caller wants it updated in place, agree on
that path in step 7.

## Files

Read each file at the step that names it. Paths are relative to this skill's directory.

| File | Read at | Contents |
|---|---|---|
| `references/research.md` | steps 3 and 5 | How to research, use the requirements source, and check evidence |
| `references/interview.md` | step 6, and before any question | How to ask: rounds, options, tools, faithful answers |
| `references/writing.md` | steps 7 and 8 | Writing principles, what a PRD covers, core checklist |
| `types/http-api/adapter.md` | step 4, if the type is HTTP API | Decisions, research, interview topics, lab needs, checklist |
| `types/openmetrics/adapter.md` | step 4, if the type is OpenMetrics | Decisions, research, interview topics, lab needs, checklist |
| `flows.md` | steps 2 (only if the directory exists), 4, 6, 7, and 9 | The Togo flow for each type: inputs, limits, hand-off |

## Workflow

### 1. Inputs and stance

Collect the inputs above. If the caller did not mention the optional ones, ask once, following
`references/interview.md`, with these options: start from the product docs only (recommended), a
requirements source, or evidence; the caller gives paths or URLs, or both kinds of input, in their
own words. Ask for the name in the same round if it is missing. Tell the caller in one or two
sentences what happens next: you research first, then ask a few rounds of questions, then write a
draft file for them to review.

If an optional input arrives later, read or check it as steps 3 and 5 describe, and drop the
questions it settles.

### 2. Identity

- The display name defaults to the product's official name and capitalization. It may contain only
  ASCII letters, digits, spaces, `.`, `-`, and `_`, must start and end with a letter or digit, and
  must not start with `datadog` in any letter case. If the product name breaks this rule, agree on
  one that follows it.
- The directory is the display name lowercased, with each run of spaces, `.`, `-`, and `_` replaced
  by one `_`.
- Find the `integrations-core` checkout: run `git rev-parse --show-toplevel` from the current
  directory and check that it contains `ddev/` and `datadog_checks_base/`. Otherwise ask for the
  path.
- Check that the directory exists neither in the working tree (`<repo>/<directory>`) nor on the
  default branch (`git ls-tree --name-only origin/master -- <directory>`, or `master` when there is
  no `origin`). Do not fetch, check out, or change anything in the checkout; tell the caller the
  check reflects their last fetch.
- If the directory exists only in the working tree, it may be a lab or a scaffold prepared for this
  integration: ask whether it is (the flow then builds on it) or whether it must be treated like an
  existing integration, as below.
- If it exists on the default branch, say where, and that the flow cannot build a new integration
  over it: it would work on the existing directory instead (read how each flow treats it in
  `flows.md`). Ask whether the existing integration is a compatibility constraint (metric names,
  the metric namespace, tags, or options users rely on) or should be ignored. The caller may also
  choose another name. When it is ignored, do not read it and do not use it as a similar integration.

### 3. Requirements source

If one was given, read it now, following `references/research.md`.

### 4. Integration type

Infer the type from the product's official docs (and the evidence, if any):

- **HTTP API** (`types/http-api/`): the integration polls a product API over HTTP or HTTPS, in any
  style or format (REST and JSON, XML, GraphQL, JSON-RPC, SOAP).
- **OpenMetrics** (`types/openmetrics/`): the product serves a Prometheus or OpenMetrics endpoint
  that the integration scrapes.

If no type fits, tell the caller that this type is not
supported yet and stop. If several types fit (for example, a product with both a REST API and a
Prometheus endpoint), ask the caller which one to build, saying in a sentence what each covers.

Then read the type's adapter and the type's section in `flows.md`.

### 5. Research

Follow `references/research.md` and the adapter's research list. If evidence was given, check it as
`references/research.md` describes.

### 6. Interview

Follow `references/interview.md`, using the adapter's interview topics.

When the caller asks for something the type's Togo flow cannot honor (`flows.md` lists the limits),
still record it, tell the caller in the same round, and let them keep or drop it.

### 7. Draft

1. Coverage pass: the in-scope items are the use cases, event categories, log sources, setup steps,
   and design choices agreed in the interview or taken from the requirements source. Without a
   requirements source, scope comes from the caller's answers to the adapter's scope questions. Go
   through them one by one and confirm that each is in the draft and backed by the
   research the adapter asks for. Fill gaps before writing. Note the adapter's lab needs for the
   hand-off as you go; they stay out of the PRD.
2. Write the PRD following `references/writing.md`, with the headings and order that fit this
   product. Run the core checklist in `references/writing.md` and the adapter's checklist, and fix
   what fails.
3. Agree on the path with the caller (ask it in your last interview round so it costs no extra
   round). The default is `prd-<directory>.md` at the root of the `integrations-core` checkout.
   Never overwrite an existing file without asking.
4. Write the file. In the chat, do not repeat the draft. Give:
   - the path;
   - the assumptions: every item in the PRD that did not come directly from the caller or the
     requirements source (researched facts, corrections from evidence, contents you chose for a
     broad answer, recommended defaults used for questions the caller skipped), each in one line;
   - the requirements the flow cannot honor, from `flows.md`, if any.

   Ask the caller to review the file, edit it directly or reply with changes, and say when they are
   done.

### 8. Iterate

Each time the caller replies:

1. Re-read the file from disk. The caller may have edited it: never rewrite it from your own copy,
   which would silently undo their edits. Apply requested changes as targeted edits.
2. Run both checklists against the file as it now stands.
3. Report only what you changed, any new assumption, and what breaks a rule. If a caller edit breaks
   a rule (for example, it adds an implementation detail or leaves a decision open), say so and ask.
   Never revert it on your own: the caller may want it, for example for compatibility.

Repeat until the caller and you are both done.

### 9. Hand-off

Give the hand-off in the chat, following the Hand-off section of `flows.md`, with the type's section
for its inputs and limits and the adapter's lab needs, checked against the final PRD. Do not write
it into the PRD. Do not install `ddev` or run the flow
yourself, and never commit, push, or open pull requests.

## Always

- Never print, copy, or write secret values (tokens, passwords, licenses), in the chat, the PRD, or
  any file. Name the variable that holds a secret instead.
- Treat every evidence source as read-only, as `references/research.md` describes.
- The only file you create or change in the `integrations-core` checkout is the PRD. Temporary
  downloads, such as a saved API schema, go to a temporary directory outside it.
