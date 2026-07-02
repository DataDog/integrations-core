# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Parse JUnit XML test reports produced by ``pytest --junit-xml``."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# CI JUnit reports never legitimately contain a DTD or entity definitions.
# Rejecting them before parsing guards against XXE / billion-laughs attacks on
# artifacts downloaded from workflow runs.
FORBIDDEN_TOKENS = ("<!DOCTYPE", "<!ENTITY")


@dataclass(frozen=True)
class FailedTest:
    """A single failed or errored test case parsed from a JUnit XML report."""

    classname: str | None
    name: str
    message: str | None
    kind: str  # "failure" | "error"

    @property
    def identifier(self) -> str:
        """A stable ``classname::name`` identifier (or just ``name`` when no classname)."""
        return f"{self.classname}::{self.name}" if self.classname else self.name


def parse_junit_failures(xml_path: Path) -> list[FailedTest]:
    """Parse one JUnit XML file and return its failed/errored test cases.

    A ``<testcase>`` counts as failed when it has a direct ``<failure>`` or
    ``<error>`` child; ``<skipped>`` cases are ignored. Malformed XML raises
    ``ET.ParseError``; a report carrying a DTD/entity definition raises ``ValueError``.
    """
    text = xml_path.read_text(encoding="utf-8")
    if any(token in text for token in FORBIDDEN_TOKENS):
        raise ValueError(f"Refusing to parse JUnit report with a DTD/entity definition: {xml_path}")

    root = ET.fromstring(text)
    failures: list[FailedTest] = []
    for testcase in root.iter("testcase"):
        for kind in ("failure", "error"):
            element = testcase.find(kind)
            if element is not None:
                failures.append(
                    FailedTest(
                        classname=testcase.get("classname") or None,
                        name=testcase.get("name", ""),
                        message=element.get("message"),
                        kind=kind,
                    )
                )
                break
    return failures


def parse_junit_dir(root: Path) -> list[FailedTest]:
    """Recursively parse every ``*.xml`` under *root*, aggregating failures.

    Files that fail to parse (malformed or DTD-bearing) are skipped silently so a
    single bad report does not abort the whole gather.
    """
    failures: list[FailedTest] = []
    for xml_path in sorted(root.rglob("*.xml")):
        try:
            failures.extend(parse_junit_failures(xml_path))
        except (ET.ParseError, ValueError, OSError):
            continue
    return failures
