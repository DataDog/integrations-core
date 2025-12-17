from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class PullRequest(BaseModel):
    number: int
    title: str
    pass_quality_gates: bool | None = None


class SizeValues(BaseModel):
    bytes: float
    human_readable: str

    def calculate_human_readable(self, bytes: float) -> str:
        sign = "-" if bytes < 0 else ""
        size = abs(bytes)
        for unit in ["B", "KiB", "MiB"]:
            if size < 1024:
                return f"{sign}{size:0.2f} {unit}" if unit != "B" else f"{sign}{size} {unit}"
            size /= 1024
        return f"{sign}{size:0.2f} GiB"

    def __add__(self, other: SizeValues) -> SizeValues:
        bytes = self.bytes + other.bytes
        return SizeValues(bytes=bytes, human_readable=self.calculate_human_readable(bytes))

    def __sub__(self, other: SizeValues) -> SizeValues:
        bytes = self.bytes - other.bytes
        return SizeValues(bytes=bytes, human_readable=self.calculate_human_readable(bytes))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SizeValues):
            return False
        return self.bytes == other.bytes

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, SizeValues):
            return True
        return not self == other


class SizePair(BaseModel):
    compressed: SizeValues
    uncompressed: SizeValues

    def __add__(self, other: "SizePair") -> "SizePair":
        return SizePair(
            compressed=self.compressed + other.compressed,
            uncompressed=self.uncompressed + other.uncompressed,
        )

    def __sub__(self, other: "SizePair") -> "SizePair":
        return SizePair(
            compressed=self.compressed - other.compressed,
            uncompressed=self.uncompressed - other.uncompressed,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SizePair):
            return False
        return self.compressed == other.compressed and self.uncompressed == other.uncompressed

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, SizePair):
            return True
        return not self == other


class SizeBlock(BaseModel):
    declared: SizePair | None
    locked: SizePair | None

    def __init__(self, **data):
        super().__init__(**data)

    @model_validator(mode="after")
    def validate_size_block(self) -> SizeBlock:
        if self.declared is None and self.locked is None:
            raise ValueError("At least one of 'declared' or 'locked' must not be None.")
        return self

    def __add__(self, other: "SizeBlock") -> "SizeBlock":
        if self.declared is None and other.declared is None:
            new_declared = None
        elif self.declared and other.declared:
            new_declared = self.declared + other.declared
        else:
            raise ValueError("Both SizeBlock objects must have `declared` set or both must be None.")

        if self.locked is None and other.locked is None:
            new_locked = None
        elif self.locked and other.locked:
            new_locked = self.locked + other.locked
        else:
            raise ValueError("Both SizeBlock objects must have `locked` set or both must be None.")

        return SizeBlock(declared=new_declared, locked=new_locked)

    def __sub__(self, other: "SizeBlock") -> "SizeBlock":
        if self.declared is None and other.declared is None:
            new_declared = None
        elif self.declared and other.declared:
            new_declared = self.declared - other.declared
        else:
            raise ValueError("Both SizeBlock objects must have `declared` set or both must be None.")

        if self.locked is None and other.locked is None:
            new_locked = None
        elif self.locked and other.locked:
            new_locked = self.locked - other.locked
        else:
            raise ValueError("Both SizeBlock objects must have `locked` set or both must be None.")

        return SizeBlock(declared=new_declared, locked=new_locked)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SizeBlock):
            return False
        return self.declared == other.declared and self.locked == other.locked

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, SizeBlock):
            return True
        return not self == other


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

    def __sub__(self, other: "PlatformSize") -> "PlatformSize":
        if self.platform != other.platform or self.python_version != other.python_version:
            raise ValueError("Platform sizes must have the same platform and python version.")
        return PlatformSize(platform=self.platform, python_version=self.python_version, size=self.size - other.size)


class CommitSize(BaseModel):
    commit_sha: str
    pull_request: PullRequest
    modules_sizes: list[ModuleSize]
    platforms_size: list[PlatformSize]

    @model_validator(mode="after")
    def validate_commit(self) -> CommitSize:
        python_versions = {module.python_version for module in self.modules_sizes}
        if len(python_versions) > 1:
            raise ValueError(f"All modules must have the same python_version, got: {python_versions}")
        return self

    def filter(
        self,
        platform: str | None = None,
        python_version: str | None = None,
        type: Literal["integration", "dependency"] | None = None,
        name: str | None = None,
        version: str | None = None,
    ) -> list[ModuleSize]:
        filters = {k: v for k, v in locals().items() if k != "self" and v is not None}

        filtered_modules = [
            module_size
            for module_size in self.modules_sizes
            if all(getattr(module_size, key) == value for key, value in filters.items())
        ]

        return filtered_modules
