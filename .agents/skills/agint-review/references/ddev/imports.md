# ddev: imports and startup

ddev is a CLI tool. Every import that runs at module load time runs *every time* a user types `ddev`, including `ddev --help`, and in every CI job that calls it. A heavy import at the top of a command module is paid by every invocation, even ones that don't use it.

## Don't add to what `import ddev.cli` loads

Don't add a module that `import ddev.cli` doesn't already load. Check with:

```shell
python -X importtime -c "import ddev.cli"
```

Always loaded anyway, so importing them at the top costs nothing: `click`, `rich`, `pydantic`, `httpx`, `requests`, `yaml`, `jinja2`, `packaging`, `datadog_checks.dev`. Heavy ones to keep lazy, imported inside the function that uses them: `matplotlib`, `datadog_api_client`, `anthropic` (**Suggestion**).

If you think a module is imported at the top and shouldn't be, follow the import chain from `ddev.cli` and check whether it's loaded anyway before commenting.

## When a heavy import has to be top-level

Sometimes a definition needs a top-level import: models, decorators or clients that must resolve at module scope and that tests import directly. Then the command becomes a package with a light `__init__.py` that holds only the Click command and imports the heavy modules inside the command body, as `ddev/src/ddev/cli/ci/tests/` does:

```text
ddev/src/ddev/cli/<group>/<command>/
├── __init__.py      # the Click command only; imports the modules below inside the command body
├── client.py        # heavy imports are fine here: this module loads only when the command runs
└── models.py        # top-level models, directly testable
```

## No side effects at import time

Command modules don't do anything at import time beyond defining things: no logging configuration, no environment changes, no I/O. `cli/env/start.py` runs `logging.basicConfig(level=INFO)` on every ddev run, which is why httpx logs leak into unrelated commands (**Request**).
