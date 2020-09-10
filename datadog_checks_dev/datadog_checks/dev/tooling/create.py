# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from datetime import datetime
from uuid import uuid4

from ..utils import (
    create_file,
    dir_exists,
    ensure_parent_dir_exists,
    path_join,
    read_file,
    read_file_binary,
    write_file,
    write_file_binary,
)
from .utils import kebab_case_name, normalize_package_name

TEMPLATES_DIR = path_join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'integration')
BINARY_EXTENSIONS = ('.png',)
SIMPLE_NAME = r'^\w+$'


def get_valid_templates():
    return sorted(os.listdir(TEMPLATES_DIR))


def construct_template_fields(integration_name, repo_choice, **kwargs):
    normalized_integration_name = normalize_package_name(integration_name)
    check_name_kebab = kebab_case_name(integration_name)

    datadog_checks_base_req = 'datadog-checks-base[deps]>=6.6.0'
    third_party_install_info = f"""\
To install the {integration_name} check on your host:


1. Install the [developer toolkit]
(https://docs.datadoghq.com/developers/integrations/new_check_howto/#developer-toolkit)
 on any machine.

2. Run `ddev release build {normalized_integration_name}` to build the package.

3. [Download the Datadog Agent](https://app.datadoghq.com/account/settings#agent).

4. Upload the build artifact to any host with an Agent and
 run `datadog-agent integration install -w
 path/to/{normalized_integration_name}/dist/<ARTIFACT_NAME>.whl`."""

    if repo_choice == 'core':
        check_name = normalized_integration_name
        author = 'Datadog'
        email = 'help@datadoghq.com'
        email_packages = 'packages@datadoghq.com'
        install_info = (
            'The {integration_name} check is included in the [Datadog Agent][2] package.\n'
            'No additional installation is needed on your server.'.format(integration_name=integration_name)
        )
        license_header = (
            '# (C) Datadog, Inc. {year}-present\n'
            '# All rights reserved\n'
            '# Licensed under a 3-clause BSD style license (see LICENSE)'.format(year=str(datetime.utcnow().year))
        )
        support_type = 'core'
        test_dev_dep = '-e ../datadog_checks_dev'
        tox_base_dep = '-e../datadog_checks_base[deps]'
    elif repo_choice == 'marketplace':
        check_name = normalize_package_name(f"{kwargs.get('author')}_{normalized_integration_name}")
        # Updated by the kwargs passed in
        author = ''
        email = ''
        email_packages = ''
        install_info = third_party_install_info
        # Static fields
        license_header = ''
        support_type = 'partner'
        test_dev_dep = 'datadog-checks-dev'
        tox_base_dep = datadog_checks_base_req
    else:
        check_name = normalized_integration_name
        author = 'U.N. Owen'
        email = email_packages = 'friend@datadog.community'
        install_info = third_party_install_info
        license_header = ''
        support_type = 'contrib'
        test_dev_dep = 'datadog-checks-dev'
        tox_base_dep = datadog_checks_base_req
    config = {
        'author': author,
        'check_class': f"{''.join(part.capitalize() for part in normalized_integration_name.split('_'))}Check",
        'check_name': check_name,
        'integration_name': integration_name,
        'check_name_kebab': check_name_kebab,
        'email': email,
        'email_packages': email_packages,
        'guid': uuid4(),
        'license_header': license_header,
        'install_info': install_info,
        'repo_choice': repo_choice,
        'support_type': support_type,
        'test_dev_dep': test_dev_dep,
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
                # Use a special README for the marketplace/partner support_type integrations
                if template_file == 'README.md' and config.get('support_type') == 'partner':
                    template_path = path_join(TEMPLATES_DIR, 'marketplace/', 'README.md')
                    file_path = path_join("/", config.get('check_name'), "README.md")
                else:
                    template_path = path_join(root, template_file)
                    file_path = template_path.replace(template_root, '')

                file_path = f'{new_root}{file_path.format(**config)}'

                files.append(File(file_path, template_path, config, read=read))

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
