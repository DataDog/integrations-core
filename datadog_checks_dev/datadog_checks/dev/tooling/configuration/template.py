# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import yaml

from ...utils import file_exists, get_parent_dir, path_join, read_file

TEMPLATES_DIR = path_join(get_parent_dir(get_parent_dir(__file__)), 'templates', 'configuration')
VALID_EXTENSIONS = ('yaml', 'yml')


class ConfigTemplates:
    def __init__(self, paths=None):
        self.templates = {}
        self.paths = []

        if paths:
            self.paths.extend(paths)

        self.paths.append(TEMPLATES_DIR)

    def load(self, template):
        path_parts = template.split('/')
        branches = path_parts.pop().split('.')
        path_parts.append(branches.pop(0))

        possible_template_paths = (
            f'{path_join(path, *path_parts)}.{extension}' for path in self.paths for extension in VALID_EXTENSIONS
        )

        for template_path in possible_template_paths:
            if file_exists(template_path):
                break
        else:
            raise ValueError(f"Template `{'/'.join(path_parts)}` does not exist")

        if template_path in self.templates:
            data = self.templates[template_path]
        else:
            try:
                data = yaml.safe_load(read_file(template_path))
            except Exception as e:
                raise ValueError(f'Unable to parse template `{template_path}`: {e}')

            self.templates[template_path] = data

        data = deepcopy(data)
        for i, branch in enumerate(branches):
            if isinstance(data, dict):
                if branch in data:
                    data = data[branch]
                else:
                    raise ValueError(f"Template `{'/'.join(path_parts)}` has no element `{'.'.join(branches[:i + 1])}`")
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

        return data

    @staticmethod
    def apply_overrides(template, overrides):
        errors = []

        for override, value in sorted(overrides.items()):
            root = template
            override_keys = override.split('.')
            final_key = override_keys.pop()

            intermediate_error = ''

            # Iterate through all but the last key, attempting to find a dictionary at every step
            for i, key in enumerate(override_keys):
                if isinstance(root, dict):
                    if i == 0 and root.get('name') == key:
                        continue

                    if key in root:
                        root = root[key]
                    else:
                        intermediate_error = (
                            f"Template override `{'.'.join(override_keys[:i])}` has no named mapping `{key}`"
                        )
                        break
                elif isinstance(root, list):
                    for item in root:
                        if isinstance(item, dict) and item.get('name') == key:
                            root = item
                            break
                    else:
                        intermediate_error = (
                            f"Template override `{'.'.join(override_keys[:i])}` has no named mapping `{key}`"
                        )
                        break
                else:
                    intermediate_error = (
                        f"Template override `{'.'.join(override_keys[:i])}` does not refer to a mapping"
                    )
                    break

            if intermediate_error:
                errors.append(intermediate_error)
                continue

            # Force assign the desired value to the final key
            if isinstance(root, dict):
                root[final_key] = value
            elif isinstance(root, list):
                for i, item in enumerate(root):
                    if isinstance(item, dict) and item.get('name') == final_key:
                        root[i] = value
                        break
                else:
                    intermediate_error = 'Template override has no named mapping `{}`'.format(
                        '.'.join(override_keys) if override_keys else override
                    )
            else:
                intermediate_error = 'Template override `{}` does not refer to a mapping'.format(
                    '.'.join(override_keys) if override_keys else override
                )

            if intermediate_error:
                errors.append(intermediate_error)
                continue

            overrides.pop(override)

        return errors
