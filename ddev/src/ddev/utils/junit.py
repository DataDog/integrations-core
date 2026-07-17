# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Parse JUnit XML test reports produced by ``pytest --junit-xml`` (the ``xunit2`` family).

The parser deserializes the full report structure and stays free of any ci/tests concern: it reports
every test case and its outcome, not only failures, so callers decide what to surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum, auto
from pathlib import Path

from defusedxml.ElementTree import ParseError, fromstring


class JUnitResultKind(StrEnum):
    """The kind of a ``<failure>``/``<error>``/``<skipped>`` element on a test case."""

    FAILURE = auto()
    ERROR = auto()
    SKIPPED = auto()


class TestStatus(StrEnum):
    """The outcome of a single test case, derived from its result elements."""

    PASSED = auto()
    FAILED = auto()
    ERROR = auto()
    SKIPPED = auto()


@dataclass(frozen=True)
class JUnitProperty:
    name: str
    value: str


@dataclass(frozen=True)
class JUnitResult:
    """A ``<failure>``, ``<error>``, or ``<skipped>`` element."""

    kind: JUnitResultKind
    message: str | None = None
    type: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class JUnitTestCase:
    classname: str
    name: str
    time: float
    properties: tuple[JUnitProperty, ...] = ()
    results: tuple[JUnitResult, ...] = ()

    @property
    def identifier(self) -> str:
        return f"{self.classname}::{self.name}"

    @property
    def status(self) -> TestStatus:
        kinds = {result.kind for result in self.results}
        if JUnitResultKind.ERROR in kinds:
            return TestStatus.ERROR
        if JUnitResultKind.FAILURE in kinds:
            return TestStatus.FAILED
        if JUnitResultKind.SKIPPED in kinds:
            return TestStatus.SKIPPED
        return TestStatus.PASSED


@dataclass(frozen=True)
class JUnitCounts:
    tests: int
    failures: int
    errors: int
    skipped: int

    @property
    def passed(self) -> int:
        return self.tests - self.failures - self.errors - self.skipped


@dataclass(frozen=True)
class JUnitTestSuite:
    name: str
    reported_counts: JUnitCounts
    time: float
    timestamp: datetime | None
    hostname: str | None
    properties: tuple[JUnitProperty, ...] = ()
    test_cases: tuple[JUnitTestCase, ...] = ()


@dataclass(frozen=True)
class JUnitReport:
    name: str | None
    test_suites: tuple[JUnitTestSuite, ...] = field(default_factory=tuple)


RESULT_KINDS = {
    "failure": JUnitResultKind.FAILURE,
    "error": JUnitResultKind.ERROR,
    "skipped": JUnitResultKind.SKIPPED,
}


def parse_junit_report(xml_path: Path) -> JUnitReport:
    """Parse one JUnit XML file into a fully deserialized :class:`JUnitReport`.

    Accepts both a ``<testsuites>`` root and a bare ``<testsuite>`` root (pytest emits either).
    Malformed XML raises ``ParseError``; a report carrying a DTD/entity definition or other unsafe
    construct raises a ``defusedxml`` exception (a ``ValueError`` subclass). ``stdout``/``stderr`` are
    intentionally skipped — they are large and available in the full run.
    """
    root = fromstring(xml_path.read_text(encoding="utf-8"))
    if root.tag == "testsuites":
        return JUnitReport(
            name=root.get("name"),
            test_suites=tuple(parse_suite(suite) for suite in root.findall("testsuite")),
        )
    if root.tag == "testsuite":
        return JUnitReport(name=None, test_suites=(parse_suite(root),))
    # Not a JUnit report (e.g. a Cobertura coverage.xml sharing the directory); reject so directory
    # scans skip it rather than misreading its root as a test suite.
    raise ValueError(f"Not a JUnit report: root element <{root.tag}>")


def parse_suite(element) -> JUnitTestSuite:
    return JUnitTestSuite(
        name=element.get("name", ""),
        reported_counts=JUnitCounts(
            tests=int(element.get("tests", 0)),
            failures=int(element.get("failures", 0)),
            errors=int(element.get("errors", 0)),
            skipped=int(element.get("skipped", 0)),
        ),
        time=float(element.get("time", 0.0)),
        timestamp=parse_timestamp(element.get("timestamp")),
        hostname=element.get("hostname"),
        properties=parse_properties(element),
        test_cases=tuple(parse_test_case(testcase) for testcase in element.findall("testcase")),
    )


def parse_test_case(element) -> JUnitTestCase:
    results = tuple(
        JUnitResult(kind=kind, message=child.get("message"), type=child.get("type"), text=child.text)
        for child in element
        if (kind := RESULT_KINDS.get(child.tag)) is not None
    )
    return JUnitTestCase(
        classname=element.get("classname", ""),
        name=element.get("name", ""),
        time=float(element.get("time", 0.0)),
        properties=parse_properties(element),
        results=results,
    )


def parse_properties(element) -> tuple[JUnitProperty, ...]:
    container = element.find("properties")
    if container is None:
        return ()
    return tuple(
        JUnitProperty(name=prop.get("name", ""), value=prop.get("value", "")) for prop in container.findall("property")
    )


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_junit_dir(root: Path) -> list[JUnitReport]:
    """Recursively parse every ``*.xml`` under *root* into a list of :class:`JUnitReport`.

    Files that fail to parse (malformed or unsafe) are skipped silently so a single bad report does not
    abort the whole gather.
    """
    reports: list[JUnitReport] = []
    for xml_path in sorted(root.rglob("*.xml")):
        try:
            reports.append(parse_junit_report(xml_path))
        except (ParseError, ValueError, OSError):
            continue
    return reports
