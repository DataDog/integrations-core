import tomllib
from typing import Optional

import click
import requests
from rich.console import Console

from ddev.cli.application import Application


@click.command()
@click.option("--org", help="Target platform (e.g. linux-aarch64). If not specified, all platforms will be analyzed")
@click.pass_obj
def create_dashboard(
    app: Application,
    org: Optional[str],
) -> None:
    """
    Creates a dashboard with the metrics on the Datadog platform
    """
    print(get_org(app))


def get_org(app: Application, org: Optional[str] = "default") -> tuple[str, str, str]:
    config_path = app.config_file.path

    with config_path.open(mode="rb") as f:
        data = tomllib.load(f)

    org_config = data.get("orgs", {}).get(org)
    if not org_config:
        raise ValueError(f"Organization '{org}' not found in config")

    return {
        "api_key": org_config["api_key"],
        "app_key": org_config["app_key"],
        "site": org_config.get("site"),
    }


