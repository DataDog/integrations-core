from __future__ import annotations

import email
import os
import re
from pathlib import Path
from typing import NamedTuple
from zipfile import ZipFile

UNNORMALIZED_PROJECT_NAME_CHARS = re.compile(r'[-_.]+')

class WheelName(NamedTuple):
    """Helper class to manipulate wheel names."""
    # Note: this implementation ignores build tags (it drops them on parsing)
    name: str
    version: str
    python_tag: str
    abi_tag: str
    platform_tag: str

    @classmethod
    def parse(cls, wheel_name: str):
        name, _ext = os.path.splitext(wheel_name)
        parts = name.split('-')
        if len(parts) == 6:
            parts.pop(2)
        return cls(*parts)

    def __str__(self):
        return '-'.join([
            self.name, self.version, self.python_tag, self.abi_tag, self.platform_tag
        ]) + '.whl'

def normalize_project_name(name: str) -> str:
    # https://peps.python.org/pep-0503/#normalized-names
    return UNNORMALIZED_PROJECT_NAME_CHARS.sub('-', name).lower()


def extract_metadata(wheel: Path) -> email.Message:
    with ZipFile(str(wheel)) as zip_archive:
        for path in zip_archive.namelist():
            root = path.split('/', 1)[0]
            if root.endswith('.dist-info'):
                dist_info_dir = root
                break
        else:
            message = f'Could not find the `.dist-info` directory in wheel: {wheel.name}'
            raise RuntimeError(message)

        try:
            with zip_archive.open(f'{dist_info_dir}/METADATA') as zip_file:
                metadata_file_contents = zip_file.read().decode('utf-8')
        except KeyError:
            message = f'Could not find a `METADATA` file in the `{dist_info_dir}` directory'
            raise RuntimeError(message) from None

    return email.message_from_string(metadata_file_contents)
