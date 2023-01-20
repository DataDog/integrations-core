# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from contextlib import suppress
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.utils.fs import Path


class GitManager:
    def __init__(self, repo_root: Path):
        self.__repo_root = repo_root

    @property
    def repo_root(self) -> Path:
        return self.__repo_root

    @cached_property
    def current_branch(self) -> str:
        return self.capture('rev-parse', '--abbrev-ref', 'HEAD').strip()

    def get_current_branch(self) -> str:
        with suppress(AttributeError):
            del self.current_branch

        return self.current_branch

    @cached_property
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

    def get_changed_files(self) -> list[str]:
        with suppress(AttributeError):
            del self.changed_files

        return self.changed_files

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
