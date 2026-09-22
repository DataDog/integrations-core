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

    Returns None when the flow has no `integration` input, the value is not a name
    `ddev create` itself would accept, or it does not normalize to a single non-empty
    directory name. Callers must fail closed in that case rather than widening the
    boundary to `repo_root`. Rejecting anything `ddev create` would reject (e.g. a
    value containing "/") matters here specifically because `normalize_package_name`
    only touches `-_. ` characters — a path separator would otherwise survive
    normalization and let `integration` name an arbitrary directory outside the
    intended integration root.
    """
    integration = runtime_variables.get("integration")
    if not isinstance(integration, str) or not integration.strip():
        return None

    # Imported lazily: `ddev.cli` eagerly imports `ddev.cli.meta.ai`, which imports back
    # into `ddev.ai`, so importing it at module load time here would risk a circular import.
    from ddev.cli.create._naming import is_creatable_integration_name, normalize_package_name

    if not is_creatable_integration_name(integration):
        return None

    normalized = normalize_package_name(integration).strip("_")
    if not normalized or len(Path(normalized).parts) != 1:
        return None
    return repo_root / normalized
