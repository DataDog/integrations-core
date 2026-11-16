# Interview protocol

The interview settles the decisions that research cannot. It is the same in every coding agent; only
the tool that shows the questions changes.

## What to ask

- Ask only decisions and facts that research could not establish or that have several valid answers.
  A fact you found goes into the draft and the assumptions list, not into a question.
- Skip anything the requirements source, the evidence, or an earlier answer already settled.
- Ask about everything the adapter lists, even what the chosen Togo flow cannot honor (for example,
  logs, when the flow cannot collect them). The caller decides whether to keep it.

## Rounds

- At most 3 questions per round. Group related questions in the same round, and plan the rounds so
  the interview takes few of them.
- Put the recommended option first and mark it `(recommended)`.The recommended option is the
  default: if the caller skips a question or says to go on, use it. In a multi-select question,
  mark each recommended option; together they are the default.
- A question that asks for a value (a name or a path) offers the default as its option when there is
  one; otherwise the caller answers in free text.
- Give each option a short description of what it means for the integration. When it helps, an
  option may say what similar integrations do, as an example and not as the rule (for example,
  "similar message queue integrations apply limits per virtual host"). Never present an existing
  integration as the right answer.
- Use multi-select when answers are not exclusive, such as which signal groups are in scope.

## Tools

Use the agent's structured question tool when it has one, for example:

| Agent | Tool |
|---|---|
| Claude Code | `AskUserQuestion` |
| pi | `ask_user_question` (from an extension; not always installed) |
| Codex | `request_user_input` (only in some modes) |

Keep to the limits above even when the tool allows more questions or options. If the tool has no
multi-select, write the question as "pick any of: a, b, c".

Without a structured question tool, ask in the chat as a numbered list, one question per number,
with lettered options, then stop and wait for the reply:

```text
1. Which signals are in scope? Pick any of:
   a. Broker health and cluster nodes (recommended)
   b. Queue depth, including the age of the oldest message (recommended)
   c. Connection and channel churn
2. How often must the integration run by default?
   a. Every 15 seconds (recommended): the Agent default.
   b. Every 60 seconds: fewer requests on large installations.

Answer with the numbers and letters (for example "1 a b, 2 a"), or in your own words.
```

## Recording answers

- Carry every answer into the PRD with its full meaning. Keep the caller's wording for typed
  answers, and never drop a qualifier, an exception, or a listed item to shorten a sentence.
- When an answer conflicts with research, the evidence, or the requirements source, say what
  conflicts and ask; do not pick one silently.
- When the caller picks a broad option (for example, a whole signal group), its contents are not
  decided yet. Settle them in a later round together with other questions, or choose them yourself
  from the docs and list them as assumptions in the draft.
