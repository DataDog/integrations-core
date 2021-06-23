# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def normalize_source_name(source_name):
    return source_name.lower().replace(' ', '_')
