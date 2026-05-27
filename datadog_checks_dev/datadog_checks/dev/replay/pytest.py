# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


def load_check_class(import_spec: str):
    """Load a check class from an import spec like ``pkg.module:ClassName``."""
    module_name, separator, class_name = import_spec.partition(':')
    if not separator or not module_name or not class_name:
        raise ValueError(f'Invalid check class import spec: {import_spec!r}')

    module = import_module(module_name)
    return getattr(module, class_name)


def infer_check_class(check_name: str):
    """Infer the exported AgentCheck class from ``datadog_checks.<check_name>``."""
    from datadog_checks.base import AgentCheck

    module = import_module(f'datadog_checks.{check_name}')
    exported_names = getattr(module, '__all__', ())
    candidates = []
    for name in exported_names:
        obj = getattr(module, name, None)
        if isinstance(obj, type) and issubclass(obj, AgentCheck):
            candidates.append(obj)

    if len(candidates) == 1:
        return candidates[0]

    # Fallback for integrations that do not maintain __all__ but follow the standard naming convention.
    conventional_name = ''.join(part.capitalize() for part in check_name.split('_')) + 'Check'
    obj = getattr(module, conventional_name, None)
    if isinstance(obj, type) and issubclass(obj, AgentCheck):
        return obj

    if not candidates:
        raise ValueError(f'Unable to infer check class for datadog_checks.{check_name}')
    raise ValueError(
        f'Unable to infer unique check class for datadog_checks.{check_name}; candidates: '
        f'{", ".join(candidate.__name__ for candidate in candidates)}'
    )


def _find_default_ca_bundle() -> str | None:
    """Find a local CA bundle usable outside the Agent embedded runtime."""
    try:
        import certifi
    except ImportError:
        pass
    else:
        certifi_path = Path(certifi.where())
        if certifi_path.is_file():
            return str(certifi_path)

    import ssl

    default_paths = ssl.get_default_verify_paths()
    for candidate in (default_paths.cafile, '/etc/ssl/certs/ca-certificates.crt'):
        if candidate and Path(candidate).is_file():
            return candidate

    return None


def _apply_no_agent_init_config_defaults(check_name: str, init_config: dict[str, Any]) -> dict[str, Any]:
    """Add init_config defaults needed by checks that normally run inside the Agent."""
    resolved_init_config = dict(init_config)
    if check_name == 'http_check' and not resolved_init_config.get('ca_certs'):
        ca_bundle = _find_default_ca_bundle()
        if ca_bundle:
            resolved_init_config['ca_certs'] = ca_bundle
    return resolved_init_config


def build_check_instances(
    check_class: str | type | None,
    instances: list[dict[str, Any]],
    check_name: str,
    init_config: dict[str, Any] | None = None,
):
    """Build one check object per instance, preserving object state across readings."""
    if check_class is None:
        cls = infer_check_class(check_name)
    elif isinstance(check_class, str):
        cls = load_check_class(check_class)
    else:
        cls = check_class

    resolved_init_config = _apply_no_agent_init_config_defaults(check_name, init_config or {})
    return [cls(check_name, resolved_init_config, [instance]) for instance in instances]


def run_check_instances(
    check_class: str | type | None,
    instances: list[dict[str, Any]],
    dd_run_check,
    check_name: str,
    init_config: dict[str, Any] | None = None,
):
    """Run a Python check class once for each provided instance using pytest's dd_run_check fixture."""
    for check in build_check_instances(check_class, instances, check_name, init_config=init_config):
        dd_run_check(check)
