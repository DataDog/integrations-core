# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

VERSION_PATTERN = re.compile(r"(?:HAProxy|hapee-lb) version ([^,]+)")


def get_version_from_http(raw_version):
    if raw_version == "":
        return None
    else:
        return VERSION_PATTERN.search(raw_version).group(1)


def get_version_from_socket(info):
    for line in info:
        key, value = line.split(':')
        if key == 'Version':
            return value
    return ''
