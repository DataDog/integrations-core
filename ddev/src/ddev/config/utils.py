# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import tomlkit
from tomlkit.toml_document import TOMLDocument

from ddev.utils.fs import Path

SCRUBBED_VALUE = '*****'
SCRUBBED_GLOBS = ('github.token', 'pypi.auth', 'trello.token', 'orgs.*.api_key', 'orgs.*.app_key')


def save_toml_document(document: TOMLDocument, path: Path):
    path.ensure_parent_dir_exists()
    path.write_atomic(tomlkit.dumps(document), 'w', encoding='utf-8')


def create_toml_document(config: dict) -> TOMLDocument:
    return tomlkit.item(config)


def scrub_config(config: dict):
    if 'token' in config.get('github', {}):
        config['github']['token'] = SCRUBBED_VALUE

    if 'auth' in config.get('pypi', {}):
        config['pypi']['auth'] = SCRUBBED_VALUE

    if 'token' in config.get('trello', {}):
        config['trello']['token'] = SCRUBBED_VALUE

    for data in config.get('orgs', {}).values():
        for key in ('api_key', 'app_key'):
            if key in data:
                data[key] = SCRUBBED_VALUE
