# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Bridge entry point invoked from the Agent's rtloader to run a check class's
``discover(service)`` method.

The Agent serializes the listeners.Service projection to JSON, calls this
function with the check class, and receives a JSON string in return:

- ``"null"`` — discover returned None, raised, or the class has no discover().
- ``"[]"`` — discover explicitly returned an empty list.
- ``"[{...}, {...}]"`` — one entry per resolved instance config.
"""
import json
import logging
from typing import Any

from .service import Port, Service

_log = logging.getLogger(__name__)


def _run_discover(check_class: Any, service_json: str) -> str:
    """Run the discover() classmethod and return the JSON-encoded result.

    Never raises — any error is caught, logged, and returned as ``"null"``.
    """
    try:
        payload = json.loads(service_json)
        ports = tuple(
            Port(number=int(p["number"]), name=p.get("name", ""))
            for p in payload.get("ports", [])
        )
        service = Service(id=payload["id"], host=payload["host"], ports=ports)
    except Exception:
        _log.exception("discover bridge: failed to parse service payload")
        return "null"

    discover = getattr(check_class, "discover", None)
    if discover is None:
        return "null"

    try:
        result = discover(service)
    except Exception:
        _log.exception("discover bridge: %s.discover raised", getattr(check_class, "__name__", "?"))
        return "null"

    if result is None:
        return "null"

    try:
        return json.dumps(list(result))
    except (TypeError, ValueError):
        _log.exception("discover bridge: %s.discover returned non-JSON-serializable", check_class)
        return "null"
