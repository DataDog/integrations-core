# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class NoopPhase:
    @classmethod
    def validate_config(cls, phase_id, config, agents):
        return None


class StubReg:
    def contains(self, n):
        return True

    def get(self, n):
        return NoopPhase


class StubRegMissing:
    def __init__(self, missing: set[str]) -> None:
        self._missing = missing

    def contains(self, n):
        return n not in self._missing

    def get(self, n):
        return NoopPhase
