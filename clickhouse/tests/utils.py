# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import requests

METRIC_PATTERN = re.compile(r'\s+M\((?P<metric>\w+),\s*"(?P<description>[^"]+)"\)\s*\\?')


def parse_described_metrics(url):
    text = requests.get(url, timeout=10).text
    metrics = dict(match.groups() for match in METRIC_PATTERN.finditer(text))

    return {metric: description for metric, description in metrics.items() if description}


def ensure_csv_safe(s):  # no cov
    return '"{}"'.format(s) if ',' in s else s


def raise_error(*args, **kwargs):
    raise Exception('test')
