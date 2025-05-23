# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from ddev.utils.fs import Path

from . import PLATFORM


class ClonedRepo:
    def __init__(self, path: Path, original_branch: str, testing_branch: str):
        self.path = path
        self.original_branch = original_branch
        self.testing_branch = testing_branch

    def reset_branch(self):
        with self.path.as_cwd():
            # Hard reset
            PLATFORM.check_command_output(["git", "checkout", "-fB", self.testing_branch, self.original_branch])

            # Remove untracked files
            PLATFORM.check_command_output(["git", "clean", "-fd"])

            # Remove all tags
            tags_dir = self.path / ".git" / "refs" / "tags"
            if tags_dir.is_dir():
                tags_dir.remove()

    @staticmethod
    def new_branch():
        return os.urandom(10).hex()
