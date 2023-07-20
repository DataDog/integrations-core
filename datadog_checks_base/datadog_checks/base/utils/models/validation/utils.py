# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ..types import make_immutable_check_config


def make_immutable(value):
    return make_immutable_check_config(value)


def handle_deprecations(config_section, deprecations, fields, context):
    warning_method = context['warning']

    for option, data in deprecations.items():
        if option not in fields:
            continue

        message = f'Option `{option}` in `{config_section}` is deprecated ->\n'

        for key, info in data.items():
            key_part = f'{key}: '
            info_pad = ' ' * len(key_part)
            message += key_part

            for i, line in enumerate(info.splitlines()):
                if i > 0:
                    message += info_pad

                message += f'{line}\n'

        warning_method(message)
