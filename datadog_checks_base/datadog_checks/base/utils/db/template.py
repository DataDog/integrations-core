# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

def template_string(template, **kwargs):
    """
    Replace placeholders in a template string with values from kwargs.

    :param template: The template string with placeholders.
    :param kwargs: The values to replace the placeholders.
    :return: The formatted string with placeholders replaced by values.
    """
    return template.format(**kwargs)
