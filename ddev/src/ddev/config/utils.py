# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import tomlkit
from tomlkit.toml_document import TOMLDocument

from ddev.utils.fs import Path

SCRUBBED_VALUE = '*****'
SCRUBBED_GLOBS = (
    'github.token',
    'pypi.auth',
    'trello.token',
    'orgs.*.api_key',
    'orgs.*.app_key',
    'ai.anthropic_api_key',
)


def save_toml_document(document: TOMLDocument, path: Path):
    path.ensure_parent_dir_exists()
    path.write_atomic(tomlkit.dumps(document), 'w', encoding='utf-8')


def create_toml_document(config: dict) -> TOMLDocument:
    return tomlkit.item(config)


def load_toml_data(path: Path) -> dict:
    return tomlkit.loads(path.read_text())


def _scrub_path(config: dict, path: str) -> None:
    parts = path.split('.')
    nodes = [config]
    for part in parts[:-1]:
        next_nodes: list[dict] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if part == '*':
                next_nodes.extend(node.values())
            elif part in node:
                next_nodes.append(node[part])
        nodes = next_nodes
    leaf = parts[-1]
    for node in nodes:
        if isinstance(node, dict) and leaf in node:
            node[leaf] = SCRUBBED_VALUE


def scrub_config(config: dict) -> None:
    for glob in SCRUBBED_GLOBS:
        _scrub_path(config, glob)
