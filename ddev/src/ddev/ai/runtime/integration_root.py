# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

from ddev.ai.config.models import RuntimeVariables


def resolve_integration_root(repo_root: Path, runtime_variables: RuntimeVariables) -> Path | None:
    """Resolve the integration directory `ddev create check` will use for this run.

    The directory name is fully determined before scaffolding by the flow's own
    `integration` input: `ddev create check <name>` derives it via
    `normalize_package_name(name)`. Reusing that same function here (rather than
    re-deriving the name) keeps one source of truth with `ddev create`.

    Returns None when the flow has no `integration` input, or its value does not
    normalize to a non-empty directory name. Callers must fail closed in that case
    rather than widening the boundary to `repo_root`.
    """
    integration = runtime_variables.get("integration")
    if not isinstance(integration, str) or not integration.strip():
        return None

    # Imported lazily: `ddev.cli` eagerly imports `ddev.cli.meta.ai`, which imports back
    # into `ddev.ai`, so importing it at module load time here would risk a circular import.
    from ddev.cli.create._naming import normalize_package_name

    normalized = normalize_package_name(integration).strip("_")
    if not normalized:
        return None
    return repo_root / normalized
