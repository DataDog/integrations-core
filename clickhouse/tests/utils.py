# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from hashlib import sha256

import requests

METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')


def parse_described_metrics(url):
    text = requests.get(url, timeout=10).text
    metrics = dict(match.groups() for match in METRIC_PATTERN.finditer(text))

    return {metric: description for metric, description in metrics.items() if description}


def hash_password(password):  # no cov
    """This is only here in case we want to create new passwords"""
    hexed = sha256(password.encode('utf-8')).hexdigest()

    # Odd length hex can cause issues
    if len(hexed) & 1:
        hexed = '0' + hexed

    return hexed


def ensure_csv_safe(s):  # no cov
    return '"{}"'.format(s) if ',' in s else s
