# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import yaml

from .utils import file_exists, path_join, read_file


def load_spec(check_root: str):
    spec_path = get_spec_path(check_root)
    return yaml.safe_load(read_file(spec_path))


def get_spec_path(check_root: str) -> str:
    sources = [
        __get_spec_path_from_manifest,
        __get_spec_path_from_common_location,
    ]

    for source in sources:
        if (spec_path := source(check_root)) is not None:
            if not file_exists(spec_path):
                raise ValueError('No config spec found')

            return spec_path

    raise ValueError('No config spec found')


def __get_spec_path_from_common_location(check_root: str) -> str | None:
    spec_path = path_join(check_root, 'assets', 'configuration', 'spec.yaml')
    return spec_path if file_exists(spec_path) else None


def __get_spec_path_from_manifest(check_root: str) -> str | None:
    manifest_path = path_join(check_root, 'manifest.json')
    if not file_exists(manifest_path):
        return None

    manifest = json.loads(read_file(manifest_path))
    assets = manifest.get('assets', {})
    if 'integration' in assets:
        relative_spec_path = assets['integration'].get('configuration', {}).get('spec', '')
    else:
        relative_spec_path = assets.get('configuration', {}).get('spec', '')

    if not relative_spec_path:
        return None

    return path_join(check_root, *relative_spec_path.split('/'))
