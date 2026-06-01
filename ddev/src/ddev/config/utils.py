# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterator

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


def _walk_config(config: dict[str, object], glob: str) -> Iterator[tuple[dict[str, object], str]]:
    """Yield (parent_dict, leaf_key) pairs matching a dotted glob path.

    Silently yields nothing on type mismatch or missing keys.
    """
    parts = glob.split('.')

    def recurse(node: object, remaining: list[str]) -> Iterator[tuple[dict[str, object], str]]:
        if not remaining or not isinstance(node, dict):
            return
        head, *tail = remaining
        if head == '*':
            for key, child in node.items():
                if not tail:
                    yield node, key
                else:
                    yield from recurse(child, tail)
        elif head in node:
            if not tail:
                yield node, head
            else:
                yield from recurse(node[head], tail)

    yield from recurse(config, parts)


def scrub_config(config: dict):
    for glob in SCRUBBED_GLOBS:
        for parent, key in _walk_config(config, glob):
            parent[key] = SCRUBBED_VALUE
