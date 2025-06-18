import json
import os

import click
import requests

from ddev.cli.application import Application
from ddev.cli.size.utils.common_funcs import get_org


@click.command()
@click.option(
    "--dd-org",
    type=str,
    required=True,
    help="Datadog organization name taken from your config file e.g. 'default'",
)
@click.pass_obj
def create_dashboard(
    app: Application,
    dd_org: str,
) -> None:
    """
    Creates a Datadog dashboard to visualize size metrics for integrations and dependencies.
    A new dashboard is created on each run. This command does not send data to Datadog.
    To send metrics, use: `ddev size status --to-dd-org <org>`.
    """
    try:
        config_file_info = get_org(app, dd_org)
        if "api_key" not in config_file_info:
            raise RuntimeError("No API key found in config file")
        if "app_key" not in config_file_info:
            raise RuntimeError("No APP key found in config file")
        if "site" not in config_file_info:
            raise RuntimeError("No site found in config file")
        headers = {
            "DD-API-KEY": config_file_info["api_key"],
            "DD-APPLICATION-KEY": config_file_info["app_key"],
            "Content-Type": "application/json",
        }
        json_path = os.path.join(os.path.dirname(__file__), "utils", "dashboard.json")
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        response = requests.post(
            f"https://api.{config_file_info['site']}/api/v1/dashboard",
            headers=headers,
            data=json.dumps(payload),
        )

        resp_json = response.json()
        if "Forbidden" in str(resp_json.get("errors", [])):
            raise PermissionError("Access denied: your APP key doesn't have permission to create dashboards.")
        print(f"Dashboard URL: https://app.{config_file_info['site']}{resp_json['url']}")
    except Exception as e:
        app.abort(str(e))
