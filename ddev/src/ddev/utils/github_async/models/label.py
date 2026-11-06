# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub label model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Label(BaseModel):
    """A label attached to an issue or pull request.

    Field reference:
    https://docs.github.com/en/rest/issues/labels#get-a-label
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    color: str | None = None
    description: str | None = None
