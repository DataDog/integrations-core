# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pagination link parsing for the GitHub REST API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


@dataclass
class PaginationData:
    """Parsed pagination links from a GitHub API Link header."""

    first: str | None = None
    prev: str | None = None
    next: str | None = None
    last: str | None = None

    @classmethod
    def from_header(cls, header: str | None) -> Self:
        """Parse a Link header value and return a PaginationData instance."""
        if not header:
            return cls()
        links: dict[str, str] = {}
        for url, rel in _LINK_RE.findall(header):
            links[rel] = url
        return cls(
            first=links.get("first"),
            prev=links.get("prev"),
            next=links.get("next"),
            last=links.get("last"),
        )
