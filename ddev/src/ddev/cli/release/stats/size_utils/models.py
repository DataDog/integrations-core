from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import BaseModel, computed_field


class PullRequest(BaseModel):
    number: int
    title: str


class SizeValues(BaseModel):
    bytes: int

    @computed_field
    def human_readable(self) -> str:
        sign = "-" if self.bytes < 0 else ""
        size = abs(self.bytes)
        for unit in ["B", "KiB", "MiB"]:
            if size < 1024:
                return f"{sign}{size:0.2f} {unit}" if unit != "B" else f"{sign}{size} {unit}"
            size /= 1024
        return f"{sign}{size:0.2f} GiB"

    def __add__(self, other: "SizeValues") -> "SizeValues":
        return SizeValues(bytes=self.bytes + other.bytes)


class SizePair(BaseModel):
    compressed: SizeValues
    uncompressed: SizeValues

    def __add__(self, other: "SizePair") -> "SizePair":
        return SizePair(
            compressed=self.compressed + other.compressed,
            uncompressed=self.uncompressed + other.uncompressed,
        )


class SizeBlock(BaseModel):
    declared: SizePair | None
    locked: SizePair | None

    def __init__(self, **data):
        super().__init__(**data)
        if self.declared is None and self.locked is None:
            raise ValueError("At least one of 'declared' or 'locked' must not be None.")

    def __add__(self, other: "SizeBlock") -> "SizeBlock":
        if self.declared is None and other.declared is None:
            new_declared = None
        elif self.declared is None:
            new_declared = other.declared
        elif other.declared is None:
            new_declared = self.declared
        else:
            new_declared = self.declared + other.declared

        if self.locked is None and other.locked is None:
            new_locked = None
        elif self.locked is None:
            new_locked = other.locked
        elif other.locked is None:
            new_locked = self.locked
        else:
            new_locked = self.locked + other.locked

        return SizeBlock(declared=new_declared, locked=new_locked)


class ModuleSize(BaseModel):
    name: str
    version: str
    platform: str
    type: Literal["integration", "dependency"]
    python_version: str
    module_sha: str
    size: SizeBlock


class PlatformSize(BaseModel):
    platform: str
    python_version: str
    size: SizeBlock


class CommitSize(BaseModel):
    commit_sha: str
    pull_request: PullRequest
    modules_sizes: list[ModuleSize]

    @computed_field
    @cached_property
    def platforms_size(self) -> list[PlatformSize]:
        agg: dict[tuple[str, str], SizeBlock] = {}

        for module in self.modules_sizes:
            key = (module.platform, module.python_version)

            if key not in agg:
                agg[key] = module.size
            else:
                agg[key] = agg[key] + module.size

        return [PlatformSize(platform=p, python_version=py, size=s) for (p, py), s in agg.items()]

    def filter(
        self,
        platform: str | None = None,
        python_version: str | None = None,
        type: Literal["integration", "dependency"] | None = None,
        name: str | None = None,
        version: str | None = None,
    ) -> CommitSize | None:
        filters = {k: v for k, v in locals().items() if k != "self" and v is not None}

        filtered_modules = [
            size for size in self.modules_sizes if all(getattr(size, key) == value for key, value in filters.items())
        ]

        return (
            CommitSize(commit_sha=self.commit_sha, pull_request=self.pull_request, modules_sizes=filtered_modules)
            if filtered_modules
            else None
        )

    def join(self, other: CommitSize) -> CommitSize:
        if self.commit_sha != other.commit_sha or self.pull_request != other.pull_request:
            raise ValueError("Commit sizes must have the same commit sha and pull request.")
        return CommitSize(
            commit_sha=self.commit_sha,
            pull_request=self.pull_request,
            modules_sizes=self.modules_sizes + other.modules_sizes,
        )

    def append(self, other: ModuleSize) -> None:
        self.modules_sizes.append(other)
