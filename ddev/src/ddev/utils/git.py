# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

    def current_branch(self) -> str:
        return self.capture('rev-parse', '--abbrev-ref', 'HEAD').strip()

    def latest_commit(self) -> GitCommit:
        sha, subject = self.capture('log', '-1', '--format=%H%n%s').splitlines()
        return GitCommit(sha, subject=subject)

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
        changed_files.update(self.capture('ls-files', '--others', '--exclude-standard').splitlines())

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

    @staticmethod
    def __is_warning_line(line):
        return line.startswith('warning: ') or 'original line endings' in line
