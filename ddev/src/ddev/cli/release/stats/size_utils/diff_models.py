from typing import Literal

from pydantic import BaseModel

from .size_models import PullRequest, SizeBlock


class PercentagePair(BaseModel):
    compressed: float
    uncompressed: float


class PercentageBlock(BaseModel):
    declared: PercentagePair
    locked: PercentagePair | None


class DiffSizeBlock(BaseModel):
    status: Literal["added", "removed", "modified", "unchanged"]
    percentage_diff: PercentageBlock | None  # if the status is "added" or "removed", the percentage_diff is None
    size_diff: SizeBlock


class DiffSize(BaseModel):
    name: str
    version: str
    platform: str
    python_version: str
    type: Literal["integration", "dependency"]
    diff: DiffSizeBlock
    baseline_size: SizeBlock | None
    target_size: SizeBlock | None


class PlatformDiff(BaseModel):
    platform: str
    python_version: str
    diff_sizes: DiffSizeBlock
    baseline_size: SizeBlock | None
    target_size: SizeBlock | None


class CommitDiff(BaseModel):
    baseline_commit_sha: str
    target_commit_sha: list[str]
    pull_request: list[PullRequest]
    diff_sizes: list[DiffSize]
    platforms_diff: list[PlatformDiff]
