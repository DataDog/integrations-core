# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def repo_to_override(app: Application) -> str:
    from ddev.utils.metadata import (
        InvalidMetadataError,
        PyProjectNotFoundError,
        RepoNotFoundError,
        ValidRepo,
        pyproject_metadata,
    )

    try:
        metadata = pyproject_metadata()
        if metadata is None:
            raise RepoNotFoundError()
        repo = metadata.repo.value
    except (PyProjectNotFoundError, RepoNotFoundError):
        app.display_error(
            "The current repo could not be inferred. Either this is not a repository or the root of "
            "the repo is missing the ddev tool configuration in its pyproject.toml file."
        )

        repo = app.prompt(
            "What repo are you trying to override? ",
            type=click.Choice([item.value for item in ValidRepo]),
            show_choices=True,
        )
    except InvalidMetadataError as e:
        from rich.markup import escape

        # Ensure escaping to avoid rich reading the table name as style markup
        app.display_error(escape(str(e)))
        app.abort()
    except Exception as e:
        app.display_error(f"An unexpected error occurred: {e}")
        app.abort()

    return repo


@click.command()
@click.pass_obj
def override(app: Application):
    """
    Overrides the repo configuration with a `.ddev.toml` file in the current working directory.

    The command tries to identify the repo you are in by reading the `repo` field in the `[tool.ddev]` table in
    the `pyproject.toml` file located at the root of your git repository.

    If the current directory is not part of a git repository, the repository root does not have a `pyproject.toml`
    file, or the file exists but has no `[tool.ddev]` table, you will be prompted to specify which repo
    configuration to override.
    """
    from rich.syntax import Syntax

    from ddev.config.file import DDEV_TOML, RootConfig, deep_merge_with_list_handling
    from ddev.config.utils import scrub_config
    from ddev.utils.fs import Path
    from ddev.utils.toml import dumps_toml_data

    app.config_file.overrides_path = Path.cwd() / DDEV_TOML
    repo = repo_to_override(app)

    local_repo_config = {
        "repo": repo,
        "repos": {repo: str(app.config_file.overrides_path.resolve().parent)},
    }

    if app.config_file.overrides_path.exists():
        app.display_info("Local config file already exists. Updating...")
        local_config = app.config_file.overrides_model.raw_data
        config = deep_merge_with_list_handling(local_config, local_repo_config)
    else:
        config = local_repo_config

    app.config_file.overrides_model = RootConfig(config)
    app.config_file.update()

    app.display_success(f"Local repo configuration added in {app.config_file.pretty_overrides_path}\n")
    app.display("Local config content:")
    scrub_config(app.config_file.overrides_model.raw_data)
    app.output(
        Syntax(dumps_toml_data(app.config_file.overrides_model.raw_data).rstrip(), "toml", background_color="default")
    )
