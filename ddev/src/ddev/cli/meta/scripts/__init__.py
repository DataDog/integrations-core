# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.meta.scripts.github_user import email2ghuser
from datadog_checks.dev.tooling.commands.meta.scripts.metrics2md import metrics2md
from datadog_checks.dev.tooling.commands.meta.scripts.remove_labels import remove_labels

from ddev.cli.meta.scripts.dynamicd import dynamicd
from ddev.cli.meta.scripts.generate_metrics import generate_metrics
from ddev.cli.meta.scripts.monitor import monitor
from ddev.cli.meta.scripts.saved_views import sv
from ddev.cli.meta.scripts.serve_openmetrics_payload import serve_openmetrics_payload
from ddev.cli.meta.scripts.update_py_config import update_python_config
from ddev.cli.meta.scripts.upgrade_python import upgrade_python_version


@click.group(short_help='Miscellaneous scripts that may be useful')
def scripts():
    """
    Miscellaneous scripts that may be useful.
    """


scripts.add_command(dynamicd)
scripts.add_command(email2ghuser)
scripts.add_command(generate_metrics)
scripts.add_command(metrics2md)
scripts.add_command(remove_labels)
scripts.add_command(serve_openmetrics_payload)
scripts.add_command(update_python_config)
scripts.add_command(upgrade_python_version)
scripts.add_command(sv)
scripts.add_command(monitor)
