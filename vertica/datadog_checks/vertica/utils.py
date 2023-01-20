# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def parse_major_version(version_string):
    return int(version_string.split('.')[0].lstrip('v'))
