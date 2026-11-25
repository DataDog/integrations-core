# Research before asking

Do the factual work yourself, before the interview and again after it for anything the caller added.
Facts you find go into the draft and the assumptions list. Only decisions go to the caller. Research
serves two ends: asking better questions and stating product facts. Never turn it into instructions
for the builder (how to read the docs, paginate, or handle errors).

## The requirements source

The requirements source is the caller's voice.

- Keep its decisions and its wording. Do not ask again what it already decides.
- When research contradicts it (for example, it names an endpoint or a version that does not exist),
  raise the conflict as a question. Never correct it silently.
- Keep its names and design (metric names, option names, a collection strategy) as written. Raise
  them only when they conflict with research (for example, a metric the product does not expose)
  or with what a PRD holds (implementation details or rules for agents).
- Anything it leaves open is researched or asked like any other topic.

## Product facts

Look these up in official sources (the vendor's docs, its public source repository, its official
container images), plus what the type's adapter lists:

- what the product does, and the terms its docs use for its main resources;
- deployment models (self-hosted, SaaS, container, Kubernetes) and editions, and whether they expose
  the same monitoring interface;
- the current release and the supported version range, and which versions changed the monitoring
  interface;
- how the product is monitored, which decides the integration type;
- authentication and the least-privileged role or setting that can read what the integration needs;
- the setup the customer must do for the integration to work (enable an endpoint or a feature,
  create a read-only account or key, start a read-only server);
- a documentation page for each concept behind an in-scope signal. Do this after the interview too,
  once the scope is known.

Use public, non-sensitive search queries only. Never put credentials, private URLs, or customer data
into a search.

Stop researching a topic once you can state the fact or the options for the question. When a
document is large (for example, a multi-megabyte OpenAPI file), do not read it whole: give a
subagent the document and the specific questions when your agent has subagents, or save it once to a
temporary directory and search it.

## Links

The PRD's documentation links point whoever builds the integration to the right pages. They come
with no instructions on how to use them.

- Include only links you opened successfully in this session, using the exact URL you landed on
  (after redirects).
- Pin a link to a version when its content depends on one: a source link uses the release tag, not
  the default branch; versioned docs use the version the PRD targets.
- Prefer official docs and source. Do not cite blogs, forums, or mirrors.

## Similar integrations

You may look at one or two existing integrations in `integrations-core` for similar products, only
to understand what users of this kind of product monitor and to suggest options in questions. Do
not use them as a source for the PRD's content, design, or names: many are old or repeat patterns
we do not want to copy. Compatibility with an existing integration is settled in the identity step,
not here.

## Evidence

When the caller gives evidence, always check it, and compare what it shows with the docs. When your
agent has subagents, do the check in one: give it the evidence, the doc links you found, and the
questions, and ask for findings with their evidence and the open unknowns.

Access is read-only:

- Never stop, restart, edit, or remove containers, volumes, images, or files of a lab, and never run
  commands inside a container that change its state.
- Read the Compose file and any seed scripts; list services and ports (`docker compose ps`, `docker
  ps`); read bounded logs; call only operations the docs describe as reads, whatever the HTTP method
  (some APIs change configuration through GET, and some read through POST).
- If a lab is given but not running, ask before starting it, and say that starting it creates
  containers and volumes. Start it only with its own command.
- Never print secrets:
  - do not read the values in `.env` files; check that a variable is set in your shell without
    printing it (`[ -n "${VAR+x}" ]`);
  - pass credentials to requests as variable references, never as literal values, and do not use
    verbose modes that print headers (such as `curl -v`);
  - redact tokens and passwords from any output you show, including logs, and ask a subagent to do
    the same in its report.

What to compare: product version and edition, endpoints and their response shapes, the signals the
docs describe against what the evidence returns, authentication, and defaults. Each difference
becomes one of these, never extra scope:

- a corrected fact in the draft, listed as an assumption with its source;
- a question, when it changes a decision;
- a lab need for the hand-off, when the lab cannot exercise an in-scope signal (tell the caller in
  the chat; it stays out of the PRD).

What the evidence exposes beyond the agreed scope stays out of the PRD unless the caller adds it.
