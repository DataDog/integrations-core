# Style

-----

These are all the checkers used by our [style enforcement](../ddev/plugins.md#style).

## [ruff][ruff-github]

An extremely fast Python linter and formatter that subsumes the roles previously played by black, isort, flake8, and several flake8 plugins. The repo's centralized configuration lives under `[tool.ruff]` in the root `pyproject.toml`; per-integration `hatch lint` envs install a pinned ruff version.

### Formatting

`ruff format` is the formatter (a drop-in for black). Quote style is set to `preserve` so existing single-quoted strings are kept as-is. Run via `ddev test -fs <integration>`.

### Linting

`ruff check` enforces the rule sets selected in `[tool.ruff.lint]`:

- `E`, `W` — pycodestyle errors and warnings
- `F` — pyflakes
- `B` — flake8-bugbear (likely bugs and design problems)
- `C` — mccabe complexity
- `G` — flake8-logging-format (consistent logging format)
- `I` — isort (`datadog_checks` is configured as a first-party namespace)
- `TID252` — flake8-tidy-imports (no relative imports of parent modules)

Run via `ddev test -ls <integration>`. Use `--fix` to auto-apply fixes where ruff can.

## [Mypy][mypy-github]

A comment-based type checker allowing a mix of dynamic and static typing. This is optional for now. In order to enable `mypy` for a specific integration, open its `hatch.toml` file and add the lines in the correct section:

```
[env.collectors.datadog-checks]
check-types: true
mypy-args = [
    "--install-types",
    "--non-interactive",
]
mypy-files = [
    "datadog_checks/",
    "tests/",
]
mypy-deps = [
  "types-mock==0.1.5",
]
...
```

The `mypy-args` defines the [mypy command line option][mypy-command-line] for this specific integration. Here are some useful flags you can add:

- `--check-untyped-defs`: Type-checks the interior of functions without type annotations.
- `--disallow-untyped-defs`: Disallows defining functions without type annotations or with incomplete type annotations.

The `datadog_checks/ tests/` arguments in `mypy-files` represent the list of files that `mypy` should type check. Feel free to edit them as desired, including removing `tests/` (if you'd prefer to not type-check the test suite), or targeting specific files (when doing partial type checking). If no files are listed, `mypy` will type-check the entire integration.

Note that the default configuration lives in the root `pyproject.toml` file of the `integrations-core` repository.

### Example

Extracted from `rethinkdb`:

```python
from typing import Any, Iterator # Contains the different types used

import rethinkdb

from .document_db.types import Metric

class RethinkDBCheck(AgentCheck):
    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(RethinkDBCheck, self).__init__(*args, **kwargs)

    def collect_metrics(self, conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        """
        Collect metrics from the RethinkDB cluster we are connected to.
        """
        for query in self.queries:
            for metric in query.run(logger=self.log, conn=conn, config=self._config):
                yield metric
```

Take a look at `vsphere` or `ibm_mq` integrations for more examples.
