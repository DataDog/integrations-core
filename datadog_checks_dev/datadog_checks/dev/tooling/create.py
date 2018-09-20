# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from datetime import datetime
from uuid import uuid4

from .utils import normalize_package_name
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
SIMPLE_NAME = r'^\w+$'


def get_valid_templates():
    return sorted(os.listdir(TEMPLATES_DIR))


def construct_template_fields(integration_name, repo_choice, **kwargs):
    normalized_integration_name = normalize_package_name(integration_name)
    check_name_cap = (
        integration_name.capitalize()
        if re.match(SIMPLE_NAME, integration_name)
        else integration_name
    )

    if repo_choice == 'core':
        author = 'Datadog'
        email = 'help@datadoghq.com'
        email_packages = 'packages@datadoghq.com'
        install_info = (
            'The {check_name_cap} check is included in the [Datadog Agent][2] package, so you do not\n'
            'need to install anything else on your server.'.format(check_name_cap=check_name_cap)
        )
        license_header = (
            '# (C) Datadog, Inc. {year}\n'
            '# All rights reserved\n'
            '# Licensed under a 3-clause BSD style license (see LICENSE)\n'
            .format(year=str(datetime.now().year))
        )
        support_type = 'core'
        tox_base_dep = '../datadog_checks_base[deps]'
    else:
        author = 'U.N. Owen'
        email = email_packages = 'friend@datadog.community'
        install_info = (
            'The {} check is not included in the [Datadog Agent][2] package, so you will\n'
            'need to install it yourself.'.format(check_name_cap)
        )
        license_header = ''
        support_type = 'contrib'
        tox_base_dep = 'datadog-checks-base[deps]'

    config = {
        'author': author,
        'check_class': '{}Check'.format(
            ''.join(part.capitalize() for part in normalized_integration_name.split('_'))
        ),
        'check_name': normalized_integration_name,
        'check_name_cap': check_name_cap,
        'email': email,
        'email_packages': email_packages,
        'guid': uuid4(),
        'license_header': license_header,
        'install_info': install_info,
        'repo_choice': repo_choice,
        'support_type': support_type,
        'tox_base_dep': tox_base_dep,
    }
    config.update(kwargs)

    return config


def create_template_files(template_name, new_root, config, read=False):
    files = []

    template_root = path_join(TEMPLATES_DIR, template_name)
    if not dir_exists(template_root):
        return files

    for root, _, template_files in os.walk(template_root):
        for template_file in template_files:
            if not template_file.endswith(('.pyc', '.pyo')):
                template_path = path_join(root, template_file)

                file_path = template_path.replace(template_root, '')
                file_path = '{}{}'.format(new_root, file_path.format(**config))

                files.append(
                    File(
                        file_path,
                        template_path,
                        config,
                        read=read
                    )
                )

    return files


class File(object):
    def __init__(self, file_path, template_path, config, read=False):
        self.file_path = file_path
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
