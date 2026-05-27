# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""In-Agent replay shim package.

This package is bind-mounted into the Datadog Agent container's embedded
Python site-packages by the ``compare-agent`` runner. A companion
``sitecustomize.py`` triggers ``bootstrap.activate()`` at interpreter
startup so each Agent sub-interpreter for a Python check has its replay
adapters installed before the check imports its HTTP client / subprocess
helpers.

The package is intentionally self-contained: it does NOT import anything
from ``datadog_checks_dev`` because that package is not part of the Agent
artifact. The original adapter source files live under
``adapters/`` and have their internal imports rewritten by the shim
builder so the same code runs both inside the Agent and in the existing
no-Agent pytest harness.
"""
