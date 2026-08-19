# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import enum
from dataclasses import dataclass

from ddev.utils.fs import Path


class ChangeType(enum.Enum):
    """The kind of change reported by `git diff --name-status`.

    Values are the literal git status letters, so a status code maps straight onto a member.
    """

    ADDED = 'A'
    MODIFIED = 'M'
    DELETED = 'D'
    RENAMED = 'R'
    COPIED = 'C'


# A type change (`T`) is a modification of an existing path. Any other single-path status is also
# treated as a modification, so no changed path is lost.
SINGLE_PATH_CHANGE_TYPES = {
    'A': ChangeType.ADDED,
    'M': ChangeType.MODIFIED,
    'D': ChangeType.DELETED,
    'T': ChangeType.MODIFIED,
}


@dataclass(frozen=True)
class ChangedFile:
    """A single change to one file.

    For renames and copies, `path` is the destination and `previous_path` is the source.
    """

    change_type: ChangeType
    path: str
    previous_path: str | None = None

    @property
    def affected_paths(self) -> tuple[str, ...]:
        """Every path this change touches.

        A rename also affects its source, which lost the file. A copy leaves the source untouched,
        so only the destination is affected.
        """
        if self.change_type is ChangeType.RENAMED and self.previous_path is not None:
            return (self.path, self.previous_path)

        return (self.path,)


DEFAULT_COMPARISON_BASE = 'origin/master'


@dataclass(frozen=True)
class Comparison:
    """The two points `GitRepository.changed_files` compares."""

    base: str = DEFAULT_COMPARISON_BASE
    head: str | None = None  # None compares against the working tree


def is_git_warning_line(line: str) -> bool:
    """Return whether a line of git output is an ignorable warning rather than a record."""
    return line.startswith('warning: ') or 'original line endings' in line


def parse_name_status(output: str) -> list[ChangedFile]:
    """Parse `git diff --name-status` output into change records.

    Lines are tab separated: `<status>\\t<path>`, or `<status>\\t<source>\\t<destination>` for
    renames and copies, whose status also carries a similarity score (`R100`). A line with the
    wrong field count raises rather than being dropped, so a changed path is never lost silently.
    """
    changed: list[ChangedFile] = []
    for line in output.splitlines():
        if not line or is_git_warning_line(line):
            continue

        fields = line.split('\t')
        status = fields[0][:1].upper()
        if status in ('R', 'C'):
            if len(fields) < 3:
                raise ValueError(f'Malformed rename/copy diff line: {line!r}')
            change_type = ChangeType.RENAMED if status == 'R' else ChangeType.COPIED
            changed.append(ChangedFile(change_type=change_type, path=fields[2], previous_path=fields[1]))
        else:
            if len(fields) < 2:
                raise ValueError(f'Malformed diff line: {line!r}')
            change_type = SINGLE_PATH_CHANGE_TYPES.get(status, ChangeType.MODIFIED)
            changed.append(ChangedFile(change_type=change_type, path=fields[1]))

    return changed


class GitCommit:
    def __init__(self, sha: str, *, subject: str = ''):
        self.__sha = sha
        self.__subject = subject

    @property
    def sha(self) -> str:
        return self.__sha

    @property
    def subject(self) -> str:
        return self.__subject


class GitRepository:
    def __init__(self, repo_root: Path):
        self.__repo_root = repo_root

        self.__filtered_tags: dict[str, list[str]] = {}
        self.__worktree_paths: list[Path] | None = None

    @property
    def repo_root(self) -> Path:
        return self.__repo_root

    def worktrees(self, include_root=False, only_subpaths=True) -> list[Path]:
        """Returns a list of paths to the worktrees in the repo.

        If `include_root` is True, the worktree representing the root of the repo is included.
        If `only_subpaths` is True, worktrees outside of the repo root are not included.
        """
        worktree_paths = self.__list_worktrees()

        # Use the resolved repo path because git will show the resolved path of the worktrees
        # in the porcelain output
        repo_root = self.repo_root.resolve()

        if only_subpaths:
            worktree_paths = [
                worktree_path for worktree_path in worktree_paths if worktree_path.is_relative_to(repo_root)
            ]

        result = [worktree_path for worktree_path in worktree_paths if include_root or worktree_path != repo_root]
        return result

    def __list_worktrees(self) -> list[Path]:
        """Return every worktree path, asking git once per set of worktrees.

        Callers such as `IntegrationRegistry` ask whether each of hundreds of directories is a
        worktree, and the answer only changes when this repository adds or removes one.
        """
        if self.__worktree_paths is None:
            output = self.capture('worktree', 'list', '--porcelain')
            self.__worktree_paths = [
                Path(line.split()[1]) for line in output.splitlines() if line.startswith('worktree')
            ]

        return self.__worktree_paths

    def is_worktree(self, path: Path, include_root=False, only_subpaths=True) -> bool:
        """
        Check if a path is a worktree.

        If `include_root` is True, the root of the repo is considered a worktree.
        If `only_subpaths` is True, worktrees outside of the repo root are not considered.
        """
        return path.resolve() in self.worktrees(include_root=include_root, only_subpaths=only_subpaths)

    def current_branch(self) -> str:
        return self.capture('rev-parse', '--abbrev-ref', 'HEAD').strip()

    def get_remote_url(self, remote: str = 'origin') -> str | None:
        """Return the configured URL for `remote`, or None if it isn't set."""
        try:
            url = self.capture('remote', 'get-url', remote).strip()
        except OSError:
            return None
        return url or None

    def latest_commit(self) -> GitCommit:
        sha, subject = self.capture('log', '-1', '--format=%H%n%s').splitlines()
        return GitCommit(sha, subject=subject)

    def log(self, args: list[str], n: int | None = None, source: str = "HEAD") -> list[dict[str, str]]:
        """
        The log is returned as a list of dictionaries where the keys and values of each element are
        specified from *args. These need to be provided in the format `"<key>:<git_format_placeholder>"`

        Examples:
            Get the last n commits from `myBranch` getting the hash, author and subject

            git.log("hash:%H", "author:%an", "subject:%s", n=20, source="myBranch")

        """
        if not args:
            return []

        keys: list[str] = []
        format_parts: list[str] = []
        for arg in args:
            try:
                key, format = arg.split(":", 1)
                keys.append(key)
                format_parts.append(format)
            except ValueError as e:
                raise ValueError(f"Invalid argument: {arg}. Expected format: key:format") from e

        pretty_format = "%x00".join(format_parts)
        cmd = ['--no-pager', 'log', f"--pretty=format:{pretty_format}"]
        if n is not None:
            cmd.append(f"-n {n}")

        cmd.append(source)

        command_output = self.capture(*cmd).strip().splitlines()

        commits: list[dict[str, str]] = []

        for line in command_output:
            line_parts = line.split("\x00")
            commit_dict = dict(zip(keys, line_parts, strict=True))
            commits.append(commit_dict)

        return commits

    def pull(self, ref):
        return self.capture('pull', 'origin', ref)

    def push(self, ref):
        return self.capture('push', 'origin', ref)

    def tag(self, value, message=None, ref=None):
        """
        Create a tag with an optional message, optionally at a specific commit/ref.
        """
        cmd = ['tag', value]
        if message is not None:
            cmd.extend(['--message', message])
        if ref is not None:
            cmd.append(ref)
        return self.capture(*cmd)

    def tags(self, glob_pattern=None) -> list[str]:
        """
        List the repo's tags and sort them.

        If not None, we pass `glob_pattern` as the pattern argument to `git tag --list`.
        """

        cmd = ['tag', '--list']
        if glob_pattern is not None:
            cmd.append(glob_pattern)
        return sorted(set(self.capture(*cmd).splitlines()))

    def fetch_tags(self) -> None:
        # We force because, in very rare cases, we move tags
        self.capture('fetch', '--all', '--tags', '--force')

    def changed_files(self, base: str = DEFAULT_COMPARISON_BASE, head: str | None = None) -> list[ChangedFile]:
        """Return the files that changed between two points, deepest path first.

        The comparison starts where the two points diverged, so changes made on `base` since then
        are not reported as ours. Without a `head` it runs against the working tree, which also
        picks up uncommitted and untracked files.

        The divergence point is resolved separately rather than with `git diff --merge-base`, which
        is fatal when a criss-cross history has more than one.
        """
        comparison = ['diff', '--name-status', self.merge_base(base, head or 'HEAD')]
        if head is not None:
            comparison.append(head)

        changed = {record.path: record for record in parse_name_status(self.capture(*comparison))}
        if head is None:
            # Worktrees inside the repo root show up as untracked and are not changes to this checkout
            for path in self.capture('ls-files', '--others', '--exclude-standard').splitlines():
                if not self.is_worktree(self.repo_root / path):
                    changed.setdefault(path, ChangedFile(change_type=ChangeType.ADDED, path=path))

        return self.__sort_changed_files(changed.values())

    def filter_tags(self, pattern: str) -> list[str]:
        import re

        if pattern in self.__filtered_tags:
            return self.__filtered_tags[pattern]

        tags = self.__filtered_tags[pattern] = [tag for tag in self.tags() if re.search(pattern, tag)]
        return tags

    def show_file(self, path: str, ref: str) -> str:
        return self.capture('show', f'{ref}:{path}')

    def run(self, *args):
        import subprocess

        self.__forget_worktrees(args)
        with self.repo_root.as_cwd():
            try:
                subprocess.run(['git', *args], check=True)
            except subprocess.CalledProcessError as e:
                raise OSError(str(e)) from None

    def capture(self, *args):
        import subprocess

        self.__forget_worktrees(args)
        with self.repo_root.as_cwd():
            try:
                process = subprocess.run(
                    ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True
                )
            except subprocess.CalledProcessError as e:
                raise OSError(f'{str(e)[:-1]}:\n{e.output}') from None

        return process.stdout

    def __forget_worktrees(self, args: tuple[str, ...]) -> None:
        """Drop the cached worktree paths when a command is about to change them."""
        if args[:1] == ('worktree',) and args[1:2] != ('list',):
            self.__worktree_paths = None

    def merge_base(self, ref_a: str, ref_b: str | None = "HEAD") -> str:
        """Return the commit where two refs diverged.

        Warnings are skipped because `capture` folds stderr into stdout, so an ambiguous refname
        prints one ahead of the sha. The result is fed to other commands as a ref, where a warning
        line would be taken for a commit. Output that is nothing but warnings falls back to the
        first line, which is all git can be said to have reported.
        """
        lines = self.capture('merge-base', ref_a, ref_b).splitlines()
        return next((line for line in lines if not is_git_warning_line(line)), lines[0])

    @staticmethod
    def __sort_changed_files(changed_files):
        return sorted(changed_files, key=lambda changed_file: (-changed_file.path.count('/'), changed_file.path))
