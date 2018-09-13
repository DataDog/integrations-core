# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
import importlib
import inspect
import time

import pkgutil
import click
import yaml

import datadog_checks
from .utils import CONTEXT_SETTINGS, abort, echo_waiting, echo_info, echo_success
from ..constants import get_root


SC_NAMES = {
    0: "Ok",
    1: "Warning",
    2: "Critical",
    3: "Unknown",
}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Run a check'
)
@click.argument('check')
@click.argument('config_file')
def run(check, config_file):
    """Run a check by invoking the `check()` method of the class."""
    root = get_root()

    check_path = os.path.join(root, check, 'datadog_checks')
    if not os.path.exists(check_path):
        abort("Check '{}' does not exist".format(check))

    # Tweak the module search path so we can import the check package
    check_base_path = os.path.join(root, 'datadog_checks_base')
    sys.path.insert(1, check_base_path)
    sys.path.insert(1, check_path)

    # Reload the namepace module to make the interpreter aware of the new
    # package layout after tweaking sys.path. This is only needed because
    # datadog-checks-dev is part of the same `datadog_checks` namespace as
    # all the checks.
    reload(datadog_checks)

    # Load the check module
    try:

        check_module = importlib.import_module(check)
    except ImportError as e:
        abort("Error loading check '{}': {}".format(check, e))

    # Find the check class
    check_class = None
    from datadog_checks.checks import AgentCheck
    for x in dir(check_module):
        obj = getattr(check_module, x)
        if inspect.isclass(obj) and issubclass(obj, AgentCheck):
            check_class = obj
            break
    else:
        abort("Unable to find the check class!")

    # Load the configuration file
    with open(config_file, 'r') as f:
        config = yaml.load(f.read())

    # Create the check
    init_config = config.get('init_config') or {}
    instances = config.get('instances', [])
    check_instance = check_class('vsphere', init_config, {}, instances)

    # Run the check
    from datadog_checks.stubs import aggregator
    for i, instance in enumerate(instances):
        echo_waiting("Running check '{}' with instance n.{}...".format(check, i+1))
        t0 = time.time()
        # Reset the aggregator at each run
        aggregator.reset()
        check_instance.check(instance)
        print_report(aggregator)
        echo_success("Check run done in {:.3f} seconds.".format(time.time() - t0))


def print_report(aggregator):
    """
    Nicely display what the check collected.
    """
    echo_info("")

    all_metrics = aggregator.metric_names
    echo_info("Metrics collected: {}".format(len(all_metrics)))
    for name in all_metrics:
        for m in aggregator.metrics(name):
            echo_info("  {}, {}".format(m.name, m.value))
    echo_info("")

    all_sc = aggregator.service_check_names
    echo_info("Service Checks: {}".format(len(all_sc)))
    for name in all_sc:
        for sc in aggregator.service_checks(name):
            echo_info("  {}, status: {}, tags: {}".format(sc.name, SC_NAMES.get(sc.status), sc.tags))
    echo_info("")

