# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from ddev.utils.fs import Path


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

    @property
    def repo_root(self) -> Path:
        return self.__repo_root

    def worktrees(self, include_root=False, only_subpaths=True) -> list[Path]:
        """Returns a list of paths to the worktrees in the repo.

        If `include_root` is True, the worktree representing the root of the repo is included.
        If `only_subpaths` is True, worktrees outside of the repo root are not included.
        """
        worktree_output = self.capture('worktree', 'list', '--porcelain')

        worktree_paths = [Path(line.split()[1]) for line in worktree_output.splitlines() if line.startswith('worktree')]

        # Use the resolved repo path because git will show the resolved path of the worktrees
        # in the porcelain output
        repo_root = self.repo_root.resolve()

        if only_subpaths:
            worktree_paths = [
                worktree_path for worktree_path in worktree_paths if worktree_path.is_relative_to(repo_root)
            ]

        result = [worktree_path for worktree_path in worktree_paths if include_root or worktree_path != repo_root]
        return result

    def is_worktree(self, path: Path, include_root=False, only_subpaths=True) -> bool:
        """
        Check if a path is a worktree.

        If `include_root` is True, the root of the repo is considered a worktree.
        If `only_subpaths` is True, worktrees outside of the repo root are not considered.
        """
        return path.resolve() in self.worktrees(include_root=include_root, only_subpaths=only_subpaths)

    def current_branch(self) -> str:
        return self.capture('rev-parse', '--abbrev-ref', 'HEAD').strip()

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

    def tag(self, value, message=None):
        """
        Create a tag with an optional message.
        """
        cmd = ['tag', value]
        if message is not None:
            cmd.extend(['--message', value])
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

    def changed_files(self) -> list[str]:
        changed_files = set()

        # Committed e.g.:
        # A   relative/path/to/file.added
        # M   relative/path/to/file.modified
        for line in self.capture('diff', '--name-status', 'origin/master...').splitlines():
            if not self.__is_warning_line(line):
                changed_files.add(line.split(maxsplit=1)[1])

        # Tracked
        for line in self.capture('diff', '--name-only', 'HEAD').splitlines():
            if not self.__is_warning_line(line):
                changed_files.add(line)

        # Untracked
        # Remove worktrees within the repo root as they can be untracked and should not be taken into account
        changed_files.update(
            untracked_file
            for untracked_file in self.capture('ls-files', '--others', '--exclude-standard').splitlines()
            if not self.is_worktree(self.repo_root / untracked_file)
        )

        return sorted(changed_files, key=lambda relative_path: (-relative_path.count('/'), relative_path))

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

        with self.repo_root.as_cwd():
            try:
                subprocess.run(['git', *args], check=True)
            except subprocess.CalledProcessError as e:
                raise OSError(str(e)) from None

    def capture(self, *args):
        import subprocess

        with self.repo_root.as_cwd():
            try:
                process = subprocess.run(
                    ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True
                )
            except subprocess.CalledProcessError as e:
                raise OSError(f'{str(e)[:-1]}:\n{e.output}') from None

        return process.stdout

    def merge_base(self, ref_a: str, ref_b: str | None = "HEAD") -> str:
        return self.capture('merge-base', ref_a, ref_b).splitlines()[0]

    @staticmethod
    def __is_warning_line(line):
        return line.startswith('warning: ') or 'original line endings' in line
