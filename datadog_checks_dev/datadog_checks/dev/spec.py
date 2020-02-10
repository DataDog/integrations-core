# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import yaml

from .utils import file_exists, path_join, read_file


def load_spec(check_root):
    spec_path = get_spec_path(check_root)
    return yaml.safe_load(read_file(spec_path))


def get_spec_path(check_root):
    manifest = json.loads(read_file(path_join(check_root, 'manifest.json')))
    relative_spec_path = manifest.get('assets', {}).get('configuration', {}).get('spec', '')
    if not relative_spec_path:
        raise ValueError('No config spec defined')

    spec_path = path_join(check_root, *relative_spec_path.split('/'))
    if not file_exists(spec_path):
        raise ValueError('No config spec found')

    return spec_path
