# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from importlib import import_module
from typing import Any


def load_check_class(import_spec: str):
    """Load a check class from an import spec like ``pkg.module:ClassName``."""
    module_name, separator, class_name = import_spec.partition(':')
    if not separator or not module_name or not class_name:
        raise ValueError(f'Invalid check class import spec: {import_spec!r}')

    module = import_module(module_name)
    return getattr(module, class_name)


def run_check_instances(check_class: str | type, instances: list[dict[str, Any]], dd_run_check, check_name: str):
    """Run a Python check class once for each provided instance using pytest's dd_run_check fixture."""
    cls = load_check_class(check_class) if isinstance(check_class, str) else check_class
    for instance in instances:
        check = cls(check_name, {}, [instance])
        dd_run_check(check)
