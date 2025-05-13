import json
from typing import Optional

import click
import requests

from ddev.cli.application import Application
from ddev.cli.size.common import get_org, get_valid_platforms


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
    create_datadog_dashboard(app, org)


def create_datadog_dashboard(app: Application, org: Optional[str]):
    config_file_info = get_org(app, "default")
    headers = {
        "DD-API-KEY": config_file_info["api_key"],
        "DD-APPLICATION-KEY": config_file_info["app_key"],
        "Content-Type": "application/json",
    }

    payload = {
        "title": "Disk Usage Status for Integrations and Dependencies",
        "layout_type": "ordered",
        "widgets": create_json(app),
    }

    response = requests.post(
        f"https://api.{config_file_info['site']}/api/v1/dashboard",
        headers=headers,
        data=json.dumps(payload),
    )

    resp_json = response.json()
    print(f"Dashboard URL: https://{config_file_info['site']}{resp_json['url']}")


def create_json(app):
    valid_platforms = get_valid_platforms(app.repo.path)
    widgets = []
    for size_type in ["compressed", "uncompressed"]:
        for platform in valid_platforms:
            widgets.append(
                {
                    "definition": {
                        "type": "treemap",
                        "title": f"Module {size_type} sizes in {platform}",
                        "requests": [
                            {
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query2",
                                        "query": f"avg:datadog.agent_integrations.size_analyzer.{size_type}"
                                        f"{{platform:{platform}}} by {{name}}",
                                        "aggregator": "last",
                                    }
                                ],
                                "response_format": "scalar",
                                "style": {"palette": "classic"},
                                "formulas": [
                                    {
                                        "formula": "query2",
                                        "number_format": {
                                            "unit": {
                                                "type": "canonical_unit",
                                                "unit_name": "byte_in_binary_bytes_family",
                                            }
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                }
            )

    return widgets
