# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import inspect
from io import open
import os
import yaml
from .fs import basepath, file_exists, get_parent_dir, path_join, read_file


def load_jmx_config():
    # Only called in tests of a check, so just go back one frame
    root = find_check_root(depth=1)

    check = basepath(root)
    example_config_path = path_join(root, 'datadog_checks', check, 'data', 'conf.yaml.example')
    metrics_config_path = path_join(root, 'datadog_checks', check, 'data', 'metrics.yaml')

    example_config = yaml.safe_load(read_file(example_config_path))
    metrics_config = yaml.safe_load(read_file(metrics_config_path))

    if example_config['init_config'] is None:
        example_config['init_config'] = {}

    # Avoid having to potentially mount multiple files by putting the default metrics
    # in the user-defined metric location.
    example_config['init_config']['conf'] = metrics_config['jmx_metrics']

    return example_config


def find_check_root(depth=0):
    # Account for this call
    depth += 1

    frame = inspect.currentframe()
    for _ in range(depth):
        frame = frame.f_back

    root = get_parent_dir(frame.f_code.co_filename)
    while True:
        if file_exists(path_join(root, 'setup.py')):
            break

        new_root = os.path.dirname(root)
        if new_root == root:
            raise OSError('No check found')

        root = new_root

    return root


def get_current_check_name(depth=0):
    # Account for this call
    depth += 1

    return os.path.basename(find_check_root(depth))


def get_metadata_metrics():
    # Only called in tests of a check, so just go back one frame
    root = find_check_root(depth=1)
    metadata_path = os.path.join(root, 'metadata.csv')
    metrics = {}
    with open(metadata_path) as f:
        for row in csv.DictReader(f):
            metrics[row['metric_name']] = row
    return metrics
