# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import yaml

from ...utils import file_exists, get_parent_dir, path_join, read_file

TEMPLATES_DIR = path_join(get_parent_dir(get_parent_dir(__file__)), 'templates', 'configuration')
VALID_EXTENSIONS = ('yaml', 'yml')


class ConfigTemplates(object):
    def __init__(self, paths=None):
        self.templates = {}
        self.paths = []

        if paths:
            self.paths.extend(paths)

        self.paths.append(TEMPLATES_DIR)

        self.fields = {'overrides': (self.override, lambda: {})}

    def load(self, template, parameters=None):
        path_parts = template.split('/')
        branches = path_parts.pop().split('.')
        path_parts.append(branches.pop(0))

        possible_template_paths = (
            '{}.{}'.format(path_join(path, *path_parts), extension)
            for path in self.paths
            for extension in VALID_EXTENSIONS
        )

        for template_path in possible_template_paths:
            if file_exists(template_path):
                break
        else:
            raise ValueError('Template `{}` does not exist'.format('/'.join(path_parts)))

        if template_path in self.templates:
            data = self.templates[template_path]
        else:
            try:
                data = yaml.safe_load(read_file(template_path))
            except Exception as e:
                raise ValueError('Unable to parse template `{}`: {}'.format(template_path, e))

            self.templates[template_path] = data

        data = deepcopy(data)
        for i, branch in enumerate(branches):
            if isinstance(data, dict):
                if branch in data:
                    data = data[branch]
                else:
                    raise ValueError(
                        'Template `{}` has no element `{}`'.format('/'.join(path_parts), '.'.join(branches[: i + 1]))
                    )
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('name') == branch:
                        data = item
                        break
                else:
                    raise ValueError(
                        'Template `{}` has no named element `{}`'.format(
                            '/'.join(path_parts), '.'.join(branches[: i + 1])
                        )
                    )
            else:
                raise ValueError(
                    'Template `{}.{}` does not refer to a mapping, rather it is type `{}`'.format(
                        '/'.join(path_parts), '.'.join(branches[:i]), type(data).__name__
                    )
                )

        if parameters is None:
            parameters = {}

        for parameter, (method, default) in self.fields.items():
            method(data, parameters.get(parameter, default()))

        return data

    @classmethod
    def override(cls, template, overrides):
        for override, value in sorted(overrides.items()):
            root = template
            override_keys = override.split('.')
            final_key = override_keys.pop()

            # Iterate through all but the last key, attempting to find a dictionary at every step
            for i, key in enumerate(override_keys):
                if isinstance(root, dict):
                    root = root.setdefault(key, {})
                elif isinstance(root, list):
                    for item in root:
                        if isinstance(item, dict) and item.get('name') == key:
                            root = item
                            break
                    else:
                        raise ValueError(
                            'Template override `{}` has no named mapping `{}`'.format('.'.join(override_keys[:i]), key)
                        )
                else:
                    raise ValueError(
                        'Template override `{}` does not refer to a mapping'.format('.'.join(override_keys[:i]))
                    )

            # Force assign the desired value to the final key
            if isinstance(root, dict):
                root[final_key] = value
            elif isinstance(root, list):
                for i, item in enumerate(root):
                    if isinstance(item, dict) and item.get('name') == final_key:
                        root[i] = value
                        break
                else:
                    raise ValueError(
                        'Template override has no named mapping `{}`'.format(
                            '.'.join(override_keys) if override_keys else override, final_key
                        )
                    )
            else:
                raise ValueError(
                    'Template override `{}` does not refer to a mapping'.format(
                        '.'.join(override_keys) if override_keys else override
                    )
                )
