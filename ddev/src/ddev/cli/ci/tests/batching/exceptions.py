# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Exceptions raised while constructing and validating test batch plans."""

from __future__ import annotations


class PlanningError(Exception):
    """Raised when a valid batch plan cannot be produced under the configured policy."""


class BatchValidationError(PlanningError):
    """Raised when a batch partition violates the execution contract."""
