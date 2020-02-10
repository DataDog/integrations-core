# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def default_option_example(option_name):
    return f'<{option_name.upper()}>'


def normalize_source_name(source_name):
    return source_name.lower().replace(' ', '_')
