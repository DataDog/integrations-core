# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from urllib.request import urlopen

METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')


def parse_described_metrics(url):
    with urlopen(url, timeout=10) as response:
        text = response.read().decode('utf-8')
    metrics = dict(match.groups() for match in METRIC_PATTERN.finditer(text))

    return {metric: description for metric, description in metrics.items() if description}


def ensure_csv_safe(s):  # no cov
    return '"{}"'.format(s) if ',' in s else s


def raise_error(*args, **kwargs):
    raise Exception('test')
