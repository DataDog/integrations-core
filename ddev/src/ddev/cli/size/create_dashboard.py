import json
from typing import Any

import click
import requests

from ddev.cli.application import Application
from ddev.cli.size.utils.common_funcs import get_org, get_valid_platforms


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
    Creates a dashboard with the metrics on the Datadog platform
    """
    try:
        config_file_info = get_org(app, dd_org)
        if 'api_key' not in config_file_info:
            raise RuntimeError("No API key found in config file")
        if 'app_key' not in config_file_info:
            raise RuntimeError("No APP key found in config file")
        if 'site' not in config_file_info:
            raise RuntimeError("No site found in config file")
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
        if "Forbidden" in str(resp_json.get("errors", [])):
            raise PermissionError("Access denied: your APP key doesn't have permission to create dashboards.")
        print(f"Dashboard URL: https://app.{config_file_info['site']}{resp_json['url']}")
    except Exception as e:
        app.abort(str(e))


def create_json(app: Application) -> list[dict[str, Any]]:
    valid_platforms = get_valid_platforms(app.repo.path)
    widgets: list[dict[str, Any]] = []

    for size_type in ["compressed", "uncompressed"]:
        for platform in valid_platforms:
            # Treemap widget
            widgets.append(
                {
                    "definition": {
                        "type": "treemap",
                        "title": f"{size_type.capitalize()} sizes in {platform}",
                        "requests": [
                            {
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query2",
                                        "query": f"avg:datadog.agent_integrations.size_analyzer.{size_type}"
                                        f"{{platform:{platform}}} by {{name_type,name}}",
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
            # Timeseries widget
            widgets.append(
                {
                    "definition": {
                        "title": f"Timeline of {size_type} sizes in {platform}",
                        "type": "timeseries",
                        "requests": [
                            {
                                "response_format": "timeseries",
                                "queries": [
                                    {
                                        "name": "query1",
                                        "data_source": "metrics",
                                        "query": f"sum:datadog.agent_integrations.size_analyzer.{size_type}"
                                        f"{{platform:{platform}}}",
                                    }
                                ],
                                "formulas": [
                                    {
                                        "formula": "query1",
                                        "number_format": {
                                            "unit": {
                                                "type": "canonical_unit",
                                                "unit_name": "byte_in_binary_bytes_family",
                                            }
                                        },
                                    }
                                ],
                                "style": {
                                    "palette": "dog_classic",
                                    "order_by": "values",
                                    "line_type": "solid",
                                    "line_width": "normal",
                                },
                                "display_type": "line",
                            }
                        ],
                    }
                }
            )

    return widgets
