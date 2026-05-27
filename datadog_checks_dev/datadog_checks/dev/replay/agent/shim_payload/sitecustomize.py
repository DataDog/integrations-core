# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Entrypoint installed at site-packages root inside the Agent container.

CPython's ``site.main()`` imports a top-level ``sitecustomize`` module
during interpreter startup. We use that hook to activate the replay shim
before any check imports its HTTP client or subprocess helpers.

If activation fails for any reason it must never break Agent boot — the
membership/inventory probes are the most important payload of the
``compare-agent`` runner and they still work when the shim is inert.
"""

from __future__ import annotations

try:
    from ddev_shim.bootstrap import activate as _activate
    _activate()
except Exception:  # noqa: BLE001
    import sys
    import traceback
    sys.stderr.write('[ddev_shim] sitecustomize activation failed:\n')
    traceback.print_exc()
