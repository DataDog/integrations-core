# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class NoopPhase:
    @classmethod
    def validate_config(cls, phase_id, config):
        return None


class StubReg:
    def __init__(self, import_errors: dict[str, str] | None = None) -> None:
        self.import_errors = import_errors or {}

    def contains(self, n):
        return True

    def get(self, n):
        return NoopPhase

    def format_import_errors(self):
        return "".join(f"\n{module}: {msg}" for module, msg in self.import_errors.items())


class StubRegMissing:
    def __init__(self, missing: set[str]) -> None:
        self._missing = missing
        self.import_errors: dict[str, str] = {}

    def contains(self, n):
        return n not in self._missing

    def get(self, n):
        return NoopPhase

    def format_import_errors(self):
        return ""
