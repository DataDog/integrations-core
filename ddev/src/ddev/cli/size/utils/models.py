import os
import shutil
import subprocess
import tempfile
from datetime import date
from enum import StrEnum
from types import TracebackType
from typing import Literal, NotRequired, Optional, Type, TypedDict

from ddev.cli.application import Application
from ddev.utils.fs import Path


class SizeMode(StrEnum):
    STATUS = "status"
    DIFF = "diff"


class FileDataEntry(TypedDict):
    Name: str  # Integration/Dependency name
    Version: str  # Version of the Integration/Dependency
    Size_Bytes: int  # Size in bytes
    Size: str  # Human-readable size
    Type: str  # Integration/Dependency
    Platform: str  # Target platform (e.g. linux-aarch64)
    Python_Version: str  # Target Python version (e.g. 3.12)
    Delta_Type: NotRequired[str]  # Change type (New, Removed, Modified)
    Percentage: NotRequired[float]  # Percentage of the size change


class DependencyEntry(TypedDict):
    compressed: NotRequired[int]  # Size in bytes
    uncompressed: NotRequired[int]  # Size in bytes
    version: str  # Version of the Dependency


class DeltaTypeGroup(TypedDict):
    Modules: list[FileDataEntry]
    Total: int


class CommitEntry(TypedDict):
    Size_Bytes: int  # Total size in bytes at commit
    Version: str  # Version of the Integration/Dependency at commit
    Date: date  # Commit date
    Author: str  # Commit author
    Commit_Message: str  # Commit message
    Commit_SHA: str  # Commit SHA hash


class CommitEntryWithDelta(CommitEntry):
    Delta_Bytes: int  # Size change in bytes compared to previous commit
    Delta: str  # Human-readable size change


class CommitEntryPlatformWithDelta(CommitEntryWithDelta):
    Platform: str  # Target platform (e.g. linux-aarch64)


class CLIParameters(TypedDict):
    app: Application  # Main application instance for CLI operations
    platform: str  # Target platform for analysis (e.g. linux-aarch64)
    py_version: str  # Target Python version for analysis
    compressed: bool  # Whether to analyze compressed file sizes
    format: Optional[list[str]]  # Output format options (png, csv, markdown, json)
    show_gui: bool  # Whether to display interactive visualization


class CLIParametersTimeline(TypedDict):
    app: Application  # Main application instance for CLI operations
    module: str  # Name of module to analyze
    threshold: Optional[int]  # Minimum size threshold for filtering
    compressed: bool  # Whether to analyze compressed file sizes
    format: Optional[list[str]]  # Output format options (png, csv, markdown, json)
    show_gui: bool  # Whether to display interactive visualization


class InitialParametersTimelineIntegration(CLIParametersTimeline):
    type: Literal["integration"]  # Specifies this is for integration analysis
    first_commit: str  # Starting commit hash for timeline analysis
    platform: None  # Platform not needed for integration analysis


class InitialParametersTimelineDependency(CLIParametersTimeline):
    type: Literal["dependency"]  # Specifies this is for dependency analysis
    first_commit: None  # No commit needed for dependency analysis
    platform: str  # Target platform for dependency analysis


class WrongDependencyFormat(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)


class GitRepo:
    """
    Clones the repo to a temp folder and deletes the folder on exit.
    """

    def __init__(self, url: Path | str) -> None:
        self.url = url
        self.repo_dir: str

    def __enter__(self):
        self.repo_dir = tempfile.mkdtemp()
        try:
            self._run("git status")
        except Exception:
            # If it is not already a repo
            self._run(f"git clone --quiet {self.url} {self.repo_dir}")
        return self

    def _run(self, command: str) -> list[str]:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True, cwd=self.repo_dir)
        return result.stdout.strip().split("\n")

    def get_module_commits(
        self, module_path: str, initial: Optional[str], final: Optional[str], time: Optional[str]
    ) -> list[str]:
        """
        Returns the list of commits (SHA) that modified a given module, filtered by time or commit range.

        Args:
            module_path: Integration name or path to the .deps/resolved file (for dependencies).
            initial: Optional initial commit hash.
            final: Optional final commit hash.
            time: Optional time filter (e.g. '2 weeks ago').

        Returns:
            List of commit SHAs (oldest to newest)
        """
        self._run("git fetch origin --quiet")
        self._run("git checkout origin/HEAD")
        try:
            if time:
                return self._run(f'git log --since="{time}" --reverse --pretty=format:%H -- {module_path}')
            elif not initial and not final:
                # Get all commits from first to latest
                return self._run(f"git log --reverse --pretty=format:%H -- {module_path}")
            elif not initial:
                # Get commits from first commit up to specified final commit
                return self._run(f"git log --reverse --pretty=format:%H ..{final} -- {module_path}")
            elif not final:
                # Get commits from specified initial commit up to latest
                return self._run(f"git log --reverse --pretty=format:%H {initial}..HEAD -- {module_path}")
            else:
                try:
                    self._run(f"git merge-base --is-ancestor {initial} {final}")
                except subprocess.CalledProcessError:
                    raise ValueError(f"Commit {initial} does not come before {final}")
                return self._run(f"git log --reverse --pretty=format:%H {initial}..{final} -- {module_path}")
        except subprocess.CalledProcessError as e:
            raise ValueError(
                "Failed to retrieve commit history.\n"
                "Make sure that the provided commits are correct and that your local repository is up to"
                "date with the remote"
            ) from e

    def checkout_commit(self, commit: str) -> None:
        try:
            self._run(f"git fetch --quiet --depth 1 origin {commit}")
        except subprocess.CalledProcessError as e:
            if e.returncode == 128:
                raise ValueError(
                    f"Failed to fetch commit '{commit}'.\n"
                    f"Make sure the provided commit hash is correct and that your local repository "
                    "is up to date with the remote\n"
                ) from e
        self._run(f"git checkout --quiet {commit}")

    def sparse_checkout_commit(self, commit_sha: str, module: str) -> None:
        self._run("git sparse-checkout init --cone")
        self._run(f"git sparse-checkout set {module}")
        self._run(f"git checkout {commit_sha}")

    def get_commit_metadata(self, commit: str) -> tuple[str, str, str]:
        result = self._run(f'git log -1 --date=format:"%b %d %Y" --pretty=format:"%ad\n%an\n%s" {commit}')
        date, author, message = result
        return date, author, message

    def get_creation_commit_module(self, integration: str) -> str:
        """
        Returns the first commit (SHA) where the given integration was introduced.
        """
        return self._run(f'git log --reverse --format="%H" -- {integration}')[0]

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        exception_traceback: Optional[TracebackType],
    ) -> None:
        if self.repo_dir and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
