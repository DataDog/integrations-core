# Async GitHub Client Development Guidelines

These guidelines apply to the async GitHub REST API client in this folder
(`client.py` and the Pydantic models under `models/`). Follow them whenever you
add or modify an endpoint method or a response model.

## Model fields that are a set of choices must be StrEnum

When defining the model of an API return body, never type a field as a plain
`str` when the OpenAPI description declares an `enum` for it. Always model those
fields with a `StrEnum` so the allowed values are explicit, validated, and
self-documenting.

The decision of whether a field is a fixed set of choices is made from the
OpenAPI description (see the next section), not from intuition. The distinction
is real and must be checked per field:

- `pull-request.state` declares `enum: [open, closed]`, so it must be a
  `StrEnum`, not a `str`.
- `workflow-run.status` and `workflow-run.conclusion` are plain nullable strings
  in the description with no `enum`, so they must stay `str | None`. Do not
  invent an enum for them just because the observed values look constrained.
- `check-run.status` declares six values
  (`queued`, `in_progress`, `completed`, `waiting`, `requested`, `pending`), so
  a `StrEnum` must list all six, not a guessed subset.

```python
from enum import StrEnum, auto


class PullRequestState(StrEnum):
    OPEN = auto()
    CLOSED = auto()
```

Prefer `auto()` for the values: on a `StrEnum` it generates each value as the
**lowercased member name**, with underscores preserved (`IN_PROGRESS` becomes
`"in_progress"`). Use it only when every declared enum value is exactly
`member_name.lower()`. When the API's value differs — a different case, hyphens,
or any form that isn't the lowercased name — spell the value out explicitly
instead of forcing `auto()`. For example `pull-request.author_association`
declares UPPERCASE values, so `auto()` would wrongly lowercase them and each must
be written out:

```python
class AuthorAssociation(StrEnum):
    OWNER = "OWNER"
    COLLABORATOR = "COLLABORATOR"
    # ...
```

A plain `str` field for a declared enum hides the contract and lets invalid
values pass validation silently; inventing an enum for a free-form string is
equally wrong because it rejects values the API legitimately returns.

## Validate the API shape against evidence, never assume it

Always ensure the shape of the API endpoint, including the request body and the
response schema, is validated and that every decision is backed by evidence with
a reference. Never assume a shape.

The source of truth is GitHub's official OpenAPI description, pinned to the API
version this client targets. That version is the `GITHUB_API_VERSION` constant
in `client.py` (the same value sent in the `X-GitHub-Api-Version` request
header). Always resolve the description for that exact version rather than a
hardcoded one, so this guidance stays correct when the client bumps its version.

To get the right schema:

1. Read `GITHUB_API_VERSION` from `client.py` (for example `2022-11-28`).
2. Fetch the bundled description for that version from the
   `github/rest-api-description` repository. The stable (OpenAPI 3.0) bundled
   files live under `descriptions/api.github.com/` and are named per version,
   so the file is
   `descriptions/api.github.com/api.github.com.<GITHUB_API_VERSION>.json`
   (substitute the value read in step 1).
3. Look up the schema component (for example `pull-request`, `workflow-run`,
   `check-run`) under `components.schemas` and read the field definition
   directly.

With that schema in hand:

- Treat a field as an enum only when the description declares `enum`; otherwise
  keep it as a plain string.
- When a field is optional or nullable, base that decision on the description
  (`nullable`, `required`), not on a single observed payload.
- Cite the reference for the schema decisions you make, the same way the existing
  models do in their docstrings (a `https://docs.github.com/...` or
  `rest-api-description` link).

## Document every endpoint method with a GitHub API reference

Every method in the async client that calls a GitHub API endpoint must include a
documentation block pointing at the exact endpoint it uses, and must explain what
each argument does. Use this format inside the method docstring:

```
GitHub API Documentation:
https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request
```

Follow the block with an `Args:` section that describes each argument, and a
`Returns:` section describing the wrapped response. This keeps every method
traceable to its source contract and makes the public surface self-explanatory.

## Two retry layers, and which one owns a failure

Failures are retried in two places, and adding a retry to the wrong one is the mistake this section
exists to prevent.

- **Rate limiting** (`_rate_limited_request`, with `ddev.utils.rate_limiting`) owns 403 and 429
  responses that the headers confirm are rate limiting. Re-acquiring the limiter *is* the backoff, so
  there is no sleeping or arithmetic there. Never add a sleep or a wait to this layer.
- **The retry strategy** (`_request`, with `retry.py`) owns everything else: transport failures and
  5xx. stamina executes it, so there is no backoff arithmetic here either.

The strategy wraps the rate-limit layer, never the reverse, so every attempt re-acquires the limiter
and waits out any pause the governor holds.

When adding an endpoint method, decide its default by whether the request can be **replayed**, not by
its verb:

- A GET takes the default, `retry` forwarded straight through.
- A mutation that is idempotent (sets given fields to given values, or is a no-op when repeated)
  passes `retry=retry if retry is not None else self._retry_policies.safe` and says why in the
  docstring. `update_check_run`, `update_issue_comment` and `add_labels_to_issue` are the examples.
- Any other mutation takes the default, which only retries failures that prove the request never
  reached GitHub. Widening one of these is how you get a duplicate workflow run or a second comment.

What may be retried is not configurable; `[dispatcher.github_retries]` tunes attempts and backoff
only. A config file that could widen the conditions would make a duplicate side effect a setting.

The client reports its own retries through the logger passed to it, and stays quiet when there is
none. Separately, stamina installs a process-wide `on_retry` hook that logs every scheduled retry to
the `stamina` logger, so retries are visible even with no logger injected. That hook is global, and
disabling it would also silence the unrelated `stamina.retry` in `ddev/e2e/agent/docker.py`, so it is
left alone here rather than reached into from this package.

## Reject a page size GitHub would not honour

Every endpoint method taking `per_page` must call `_ensure_per_page_valid` before its request.
GitHub's shared `per-page` parameter is documented as "max 100" but carries no maximum in its schema,
and a larger value is not refused: the API silently serves 100. Without the check, a method that only
reads the first page returns fewer results than the caller asked for and nothing says why.

## Never follow a redirect

The client does not follow redirects, because the `Authorization` header would travel to whatever
host `Location` names. An unexpected 3xx raises `GitHubUnexpectedRedirectError` naming the endpoint,
and no policy may retry one. `download_artifact` is the single endpoint whose contract is a redirect;
it opts in with `expect_redirect=True` and reads `Location` itself. Do not enable `follow_redirects`
to make a failing request work.

## One method per API endpoint

Always keep exactly one method per API endpoint. Do not create convenience
methods that chain calls across multiple endpoints to produce richer outputs.

Each method must map to a single GitHub endpoint so that behavior, error
handling, and rate-limit accounting stay predictable and one-to-one with the API.
If a caller needs a composite result, compose the single-endpoint methods at the
call site rather than hiding multiple requests behind one method.
