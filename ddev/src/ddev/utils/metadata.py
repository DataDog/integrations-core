# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from enum import Enum

from pydantic import BaseModel, ValidationError

from ddev.utils.fs import Path
from ddev.utils.git import GitRepository


class ValidRepo(Enum):
    CORE = "core"
    EXTRAS = "extras"
    INTERNAL = "internal"
    AGENT = "agent"
    MARKETPLACE = "marketplace"
    INTEGRATIONS_INTERNAL_CORE = "integrations-internal-core"


class DdevToolMetadata(BaseModel):
    repo: ValidRepo


class RepoNotFoundError(Exception):
    def __init__(self):
        super().__init__(f"Repo not found in the current directory or any parent directory: {Path.cwd()!s}")


class PyProjectNotFoundError(Exception):
    def __init__(self, repo_root: Path):
        super().__init__(f"Pyproject.toml not found in the repo: {repo_root!s}")


class InvalidMetadataError(Exception):
    def __init__(self, error: ValidationError):
        self.error = error
        super().__init__(self.message)

    @property
    def message(self) -> str:
        body = ["Invalid ddev metadata found in pyproject.toml:"]
        for error in self.error.errors():
            key = error["loc"][0]
            value = f" {error['input']!r}" if error["input"] is not None else ""

            match error["type"]:
                case "missing":
                    body.append(f"  - [tool.ddev]: The {key!r} field is required")
                case _:
                    body.append(f"  - [tool.ddev.{key}] is{value}: {error['msg']}")
        return "\n".join(body)


def pyproject_metadata(repo: GitRepository | None = None) -> DdevToolMetadata | None:
    """
    This method returns the metadata found for the ddev tool in the pyproject.toml file.

    ```toml
    [tool.ddev]
    repo = "integrations-core"
    ```

    In order to ensure we are reading the repo pyproject.toml file, and the one form a given integration,
    we would rely on checking the one in the root directory of the repo. If no repo is provided, the current
    working directory is used to find the repo root.

    If we are not in a repo, the RepoNotFoundError is raised.

    If there is no pyproject.toml file, the PyProjectNotFoundError is raised.

    If there is no `tool.ddev` table, None is returned.
    """
    from ddev.utils.toml import load_toml_file

    if repo is None:
        try:
            from subprocess import PIPE, STDOUT, CalledProcessError, run

            revparse_output = run(
                ["git", "rev-parse", "--show-toplevel"], stdout=PIPE, stderr=STDOUT, check=True, encoding="utf-8"
            ).stdout.strip()
            repo_root = Path(revparse_output)
        except CalledProcessError as e:
            raise RepoNotFoundError() from e
    else:
        repo_root = repo.repo_root

    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise PyProjectNotFoundError(repo_root)

    pyproject = load_toml_file(pyproject_path)
    if "tool" in pyproject and "ddev" in pyproject["tool"]:
        try:
            return DdevToolMetadata(**pyproject["tool"]["ddev"])
        except ValidationError as e:
            raise InvalidMetadataError(e)
    return None
