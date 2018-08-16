# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from ..utils import (
    create_file,
    dir_exists,
    ensure_parent_dir_exists,
    path_join,
    read_file,
    read_file_binary,
    write_file,
    write_file_binary
)

TEMPLATES_DIR = path_join(os.path.dirname(os.path.abspath(__file__)), 'templates')
BINARY_EXTENSIONS = ('.png', )


def get_valid_templates():
    return sorted(os.listdir(TEMPLATES_DIR))


def create_template_files(template_name, new_root, config, read=False):
    files = []

    template_root = path_join(TEMPLATES_DIR, template_name)
    if not dir_exists(template_root):
        return files

    for root, _, template_files in os.walk(template_root):
        for template_file in template_files:
            template_path = path_join(root, template_file)
            files.append(
                File(
                    template_path.replace(template_root, new_root),
                    template_path,
                    config,
                    read=read
                )
            )

    return files


class File(object):
    def __init__(self, file_path, template_path, config, read=False):
        self.file_path = file_path.format(check_name=config['check_name'])
        self.template_path = template_path
        self.config = config
        self.binary = template_path.endswith(BINARY_EXTENSIONS)
        self._read = read_file_binary if self.binary else read_file
        self._write = write_file_binary if self.binary else write_file
        self.contents = None

        if read:
            self.read()

    def read(self):
        contents = self._read(self.template_path)

        if self.binary:
            self.contents = contents
        else:
            self.contents = contents.format(**self.config)

    def write(self):
        if self.contents is None:
            create_file(self.file_path)
        else:
            ensure_parent_dir_exists(self.file_path)
            self._write(self.file_path, self.contents)
