# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from fnmatch import fnmatch

import tomlkit
from tomlkit.toml_document import TOMLDocument

from ddev.utils.fs import Path

SCRUBBED_VALUE = '*****'
SCRUBBED_GLOBS = (
    'github.token',
    'github.token_command',
    'pypi.auth',
    'trello.key',
    'trello.key_command',
    'trello.token',
    'trello.token_command',
    'dynamicd.llm_api_key',
    'dynamicd.llm_api_key_command',
    'orgs.*.api_key',
    'orgs.*.app_key',
)


def save_toml_document(document: TOMLDocument, path: Path):
    path.ensure_parent_dir_exists()
    path.write_atomic(tomlkit.dumps(document), 'w', encoding='utf-8')


def create_toml_document(config: dict) -> TOMLDocument:
    return tomlkit.item(config)


def load_toml_data(path: Path) -> dict:
    return tomlkit.loads(path.read_text())


def scrub_config(config: dict):
    _scrub_path(config, ())


def _scrub_path(value, path: tuple[str, ...]):
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                continue

            candidate_path = '.'.join((*path, key))
            if any(fnmatch(candidate_path, glob) for glob in SCRUBBED_GLOBS):
                value[key] = SCRUBBED_VALUE
                continue

            _scrub_path(item, (*path, key))
        return

    if isinstance(value, list):
        for item in value:
            _scrub_path(item, path)
