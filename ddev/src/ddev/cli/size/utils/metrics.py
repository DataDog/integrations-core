import re
import subprocess

from ddev.cli.application import Application
from ddev.cli.size.utils.general import convert_to_human_readable_size
from ddev.cli.size.utils.models import FileDataEntry, SizeMode

METRIC_VERSION = 1


def send_metrics_to_dd(
    app: Application,
    modules: list[FileDataEntry],
    org: str | None,
    key: str | None,
    site: str | None,
    compressed: bool,
    mode: SizeMode,
    commits: list[str] | None = None,
) -> None:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.metrics_api import MetricsApi
    from datadog_api_client.v2.model.metric_intake_type import MetricIntakeType
    from datadog_api_client.v2.model.metric_payload import MetricPayload
    from datadog_api_client.v2.model.metric_point import MetricPoint
    from datadog_api_client.v2.model.metric_series import MetricSeries

    metric_name = "datadog.agent_integrations"
    size_type = "compressed" if compressed else "uncompressed"
    dd_site = site if site else "datadoghq.com"
    config_file_info = app.config.orgs.get(org, {}) if org else {'api_key': key, 'site': dd_site}

    if "api_key" not in config_file_info or config_file_info["api_key"] is None or config_file_info["api_key"] == "":
        raise RuntimeError("No API key found in config file")
    if "site" not in config_file_info or config_file_info["site"] is None or config_file_info["site"] == "":
        raise RuntimeError("No site found in config file")

    timestamp, message, tickets, prs = get_commit_data(commits[-1]) if commits else get_commit_data()

    metrics = []
    n_integrations_metrics = []
    n_dependencies_metrics = []

    n_integrations: dict[tuple[str, str], int] = {}
    n_dependencies: dict[tuple[str, str], int] = {}

    gauge_type = MetricIntakeType.GAUGE

    sizes: dict[str, dict[str, int]] = {}

    for item in modules:
        delta_type = item.get('Delta_Type', '')
        metrics.append(
            MetricSeries(
                metric=f"{metric_name}.size_{mode.value}",
                type=gauge_type,
                points=[MetricPoint(timestamp=timestamp, value=item["Size_Bytes"])],
                tags=[
                    f"module_name:{item['Name']}",
                    f"module_type:{item['Type']}",
                    f"name_type:{item['Type']}({item['Name']})",
                    f"python_version:{item['Python_Version']}",
                    f"module_version:{item['Version']}",
                    f"platform:{item['Platform']}",
                    "team:agent-integrations",
                    f"compression:{size_type}",
                    f"metrics_version:{METRIC_VERSION}",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                    f"commit_message:{message}",
                    f"delta_Type:{delta_type}",
                ],
            )
        )
        if mode is SizeMode.STATUS:
            key_count = (item['Platform'], item['Python_Version'])
            if key_count not in n_integrations:
                n_integrations[key_count] = 0
            if key_count not in n_dependencies:
                n_dependencies[key_count] = 0
            if item['Type'] == 'Integration':
                n_integrations[key_count] += 1
            elif item['Type'] == 'Dependency':
                n_dependencies[key_count] += 1

    if mode is SizeMode.STATUS:
        for (platform, py_version), count in n_integrations.items():
            n_integrations_metrics.append(
                MetricSeries(
                    metric=f"{metric_name}.integration_count",
                    type=gauge_type,
                    points=[MetricPoint(timestamp=timestamp, value=count)],
                    tags=[
                        f"platform:{platform}",
                        f"python_version:{py_version}",
                        "team:agent-integrations",
                        f"metrics_version:{METRIC_VERSION}",
                    ],
                )
            )
        for (platform, py_version), count in n_dependencies.items():
            n_dependencies_metrics.append(
                MetricSeries(
                    metric=f"{metric_name}.dependency_count",
                    type=gauge_type,
                    points=[MetricPoint(timestamp=timestamp, value=count)],
                    tags=[
                        f"platform:{platform}",
                        f"python_version:{py_version}",
                        "team:agent-integrations",
                        f"metrics_version:{METRIC_VERSION}",
                    ],
                )
            )

    configuration = Configuration()
    configuration.request_timeout = (5, 5)
    configuration.api_key = {
        "apiKeyAuth": config_file_info["api_key"],
    }
    configuration.server_variables["site"] = config_file_info["site"]

    # Format the sizes dictionary into a human-readable summary
    summary_lines = []
    for platform, py_versions in sizes.items():
        for py_version, size_bytes in py_versions.items():
            summary_lines.append(
                f"Platform: {platform}, Python: {py_version}, Size: "
                f"{convert_to_human_readable_size(size_bytes)} ({size_bytes} bytes)"
            )
    summary = "\n".join(summary_lines)

    total_metrics = len(metrics) + len(n_integrations_metrics) + len(n_dependencies_metrics)

    app.display(f"Sending {total_metrics} metrics to Datadog...")

    app.display("\nMetric summary:")
    app.display(summary)

    with ApiClient(configuration) as api_client:
        api_instance = MetricsApi(api_client)

        app.display_debug(f"Sending Metrics: {metrics}")
        api_instance.submit_metrics(body=MetricPayload(series=metrics))

        if mode is SizeMode.STATUS:
            app.display_debug(f"Sending N integrations metrics: {n_integrations_metrics}")
            api_instance.submit_metrics(body=MetricPayload(series=n_integrations_metrics))

            app.display_debug(f"Sending N dependencies metrics: {n_dependencies_metrics}")
            api_instance.submit_metrics(body=MetricPayload(series=n_dependencies_metrics))

    print("Metrics sent to Datadog")


def get_commit_data(commit: str | None = "") -> tuple[int, str, list[str], list[str]]:
    '''
    Get the commit data for a given commit. If no commit is provided, get the last commit data.
    '''
    cmd = ["git", "log", "-1", "--format=%s%n%ct"]
    cmd.append(commit) if commit else None
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    cmd_branch = ["git", "branch", "--remote", "--contains"]
    cmd_branch.append(commit) if commit else cmd_branch.append("HEAD")
    branch_name = subprocess.check_output(cmd_branch).decode("utf-8")
    ticket_pattern = r'\b(?:DBMON|SAASINT|AGENT|AI)-\d+\b'
    pr_pattern = r'#(\d+)'

    message, timestamp = result.stdout.strip().split('\n')
    tickets = list(set(re.findall(ticket_pattern, message) + re.findall(ticket_pattern, branch_name)))
    prs = re.findall(pr_pattern, message)
    if not tickets:
        tickets = [""]
    if not prs:
        prs = [""]
    return int(timestamp), message, tickets, prs
