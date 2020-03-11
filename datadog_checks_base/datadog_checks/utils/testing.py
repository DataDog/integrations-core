# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import os
import sys

E2E_PREFIX = 'DDEV_E2E'


def e2e_active():
    return any(ev.startswith(E2E_PREFIX) for ev in os.environ)


def get_check_root_path():
    return sys.argv[0].split('.tox')[0]


def get_metadata_metrics():
    metadata_path = os.path.join(get_check_root_path(), 'metadata.csv')
    metrics = {}
    with open(metadata_path) as f:
        for row in csv.DictReader(f):
            metrics[row['metric_name']] = row
    return metrics
