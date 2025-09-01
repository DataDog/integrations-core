import argparse
import csv
import json

from datadog import api, initialize

from ddev.cli.size.utils.common_funcs import (
    METRIC_NAME,
    METRIC_VERSION,
    get_last_commit_data,
    get_last_commit_timestamp,
)


def convert_to_human_readable_size(size_bytes: float) -> str:
    for unit in [" B", " KiB", " MiB", " GiB"]:
        if abs(size_bytes) < 1024:
            return str(round(size_bytes, 2)) + unit
        size_bytes /= 1024
    return str(round(size_bytes, 2)) + " TB"


def calculate_diffs(prev_compressed_sizes, curr_compressed_sizes, prev_uncompressed_sizes, curr_uncompressed_sizes):
    def key(entry):
        return (
            entry.get("Name"),
            entry.get("Platform"),
            entry.get("Python_Version"),
            entry.get("Type"),
        )

    prev_compressed_map = {key(e): e for e in prev_compressed_sizes}
    curr_compressed_map = {key(e): e for e in curr_compressed_sizes}
    prev_uncompressed_map = {key(e): e for e in prev_uncompressed_sizes}
    curr_uncompressed_map = {key(e): e for e in curr_uncompressed_sizes}
    platform = curr_compressed_sizes[0]['Platform']
    python_version = curr_compressed_sizes[0]['Python_Version']

    added = []
    removed = []
    changed = []
    unchanged = []

    total_diff = 0
    # Find added and changed
    for curr_key, curr_entry in curr_compressed_map.items():
        if curr_key not in prev_compressed_map:
            # Add both compressed and uncompressed size info for added entries
            added.append(
                {
                    **{"Compressed_Size_Bytes": int(curr_entry.get("Size_Bytes", 0))},
                    "Uncompressed_Size_Bytes": int(curr_uncompressed_map.get(curr_key, {}).get("Size_Bytes", 0)),
                }
            )
            total_diff += int(curr_entry.get("Size_Bytes", 0))
        else:
            prev_entry = prev_compressed_map[curr_key]
            prev_size = int(prev_entry.get("Size_Bytes", 0))
            curr_size = int(curr_entry.get("Size_Bytes", 0))
            uncompressed_prev_size = int(prev_uncompressed_map[curr_key].get("Size_Bytes", 0))
            uncompressed_curr_size = int(curr_uncompressed_map[curr_key].get("Size_Bytes", 0))
            if prev_size != curr_size:
                compressed_percentage = ((curr_size - prev_size) / prev_size) * 100 if prev_size != 0 else 0
                uncompressed_percentage = (
                    ((uncompressed_curr_size - uncompressed_prev_size) / uncompressed_prev_size) * 100
                    if uncompressed_prev_size != 0
                    else 0
                )
                changed.append(
                    {
                        "Name": curr_entry.get("Name"),
                        "Version": curr_entry.get("Version"),
                        "Prev Version": prev_entry.get("Version"),
                        "Platform": curr_entry.get("Platform"),
                        "Python_Version": curr_entry.get("Python_Version"),
                        "Type": curr_entry.get("Type"),
                        "Prev_Size_Bytes": prev_size,
                        "Curr_Size_Bytes": curr_size,
                        "Compressed_Diff": curr_size - prev_size,
                        "Uncompressed_Diff": uncompressed_curr_size - uncompressed_prev_size,
                        "Compressed_Percentage": compressed_percentage,
                        "Uncompressed_Percentage": uncompressed_percentage,
                    }
                )
            else:
                unchanged.append(
                    {
                        "Name": curr_entry.get("Name"),
                        "Version": curr_entry.get("Version"),
                        "Prev Version": prev_entry.get("Version"),
                        "Platform": curr_entry.get("Platform"),
                        "Python_Version": curr_entry.get("Python_Version"),
                        "Type": curr_entry.get("Type"),
                        "Compressed_Diff": 0,
                        "Uncompressed_Diff": 0,
                        "Percentage": 0,
                    }
                )
            total_diff += curr_size - prev_size
    # Find removed
    for prev_key, prev_entry in prev_compressed_map.items():
        if prev_key not in curr_compressed_map:
            removed.append(
                {
                    **{"Compressed_Size_Bytes": int(prev_entry.get("Size_Bytes", 0))},
                    "Uncompressed_Size_Bytes": int(prev_uncompressed_map[prev_key].get("Size_Bytes", 0)),
                }
            )
            total_diff -= int(prev_entry.get("Size_Bytes", 0))

    return (
        {
            "added": order_by(added, "Compressed Size Bytes"),
            "removed": order_by(removed, "Compressed Size Bytes"),
            "changed": order_by(changed, "Compressed_Percentage"),
            "total_diff": total_diff,
        },
        platform,
        python_version,
    )


def order_by(diffs, key):
    return sorted(diffs, key=lambda x: x[key], reverse=True)


def display_diffs_to_html(diffs, platform, python_version):
    sign = "+" if diffs['total_diff'] > 0 else ""
    text = f"<details><summary><h4>Size Delta for {platform} and Python {python_version}:\n"
    text += f"{sign}{convert_to_human_readable_size(diffs['total_diff'])}</h4></summary>\n\n"

    if diffs["added"]:
        text += "<details><summary>Added</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th><th>Compressed Size Delta</th>"
        text += "<th>Uncompressed Size Delta</th></tr>\n"
        for entry in diffs["added"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            compressed_size = entry.get("Compressed_Size_Bytes", 0)
            uncompressed_size = entry.get("Uncompressed_Size_Bytes", 0)
            typ = entry.get("Type", "")
            text += f"<tr><td>{typ}</td><td>{name}</td><td>{version}</td><td>+{compressed_size}</td>"
            text += f"<td>+{uncompressed_size}</td></tr>\n"
        text += "</table>\n"
        text += "</details>\n\n"
    else:
        text += "No added dependencies/integrations\n\n"

    if diffs["removed"]:
        text += "<details><summary>Removed</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th><th>Compressed Size Delta</th>"
        text += "<th>Uncompressed Size Delta</th></tr>\n"
        for entry in diffs["removed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            compressed_size = int(entry.get("Compressed_Size_Bytes", 0))
            uncompressed_size = int(entry.get("Uncompressed_Size_Bytes", 0))
            typ = entry.get("Type", "")
            text += f"<tr><td>{typ}</td><td>{name}</td>"
            text += f"<td>{version}</td><td>-{convert_to_human_readable_size(compressed_size)}</td>"
            text += f"<td>-{convert_to_human_readable_size(uncompressed_size)}</td></tr>\n"
        text += "</table>\n"
        text += "</details>\n\n"
    else:
        text += "No removed dependencies/integrations\n\n"

    if diffs["changed"]:
        text += "<details><summary>Changed</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th>"
        text += "<th>Compressed Size Delta</th><th>Uncompressed Size Delta</th><th>Compressed Percentage</th>"
        text += "<th>Uncompressed Percentage</th></tr>\n"
        for entry in diffs["changed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            typ = entry.get("Type", "")
            compressed_percentage = entry.get("Compressed_Percentage", 0)
            uncompressed_percentage = entry.get("Uncompressed_Percentage", 0)
            compressed_diff = entry.get("Compressed_Diff", 0)
            uncompressed_diff = entry.get("Uncompressed_Diff", 0)
            sign = "+" if compressed_diff > 0 else "-"
            version_diff = (
                f"{entry.get('Prev Version', version)} → {entry.get('Version', version)}"
                if entry.get('Prev Version', version) != entry.get('Version', version)
                else version
            )
            text += (
                f"<tr><td>{typ}</td><td>{name}</td><td>{version_diff}</td>"
                f"<td>{sign}{convert_to_human_readable_size(abs(compressed_diff))}</td>"
                f"<td>{sign}{convert_to_human_readable_size(abs(uncompressed_diff))}</td>"
                f"<td>{sign}{compressed_percentage:.2f}%</td>"
                f"<td>{sign}{uncompressed_percentage:.2f}%</td></tr>\n"
            )
        text += "</table>\n"
        text += "</details>\n\n"
    else:
        text += "No changed dependencies/integrations\n\n"
    text += "</details>\n"
    return text


def display_diffs_to_html_short(diffs, platform, python_version):
    sign = "+" if diffs['total_diff'] > 0 else ""
    text = f"<details><summary><h4>Size Delta for {platform} and Python {python_version}:\n"
    text += f"{sign}{convert_to_human_readable_size(diffs['total_diff'])}</h4></summary>\n\n"
    total_added_compressed = sum(int(entry.get("Compressed_Size_Bytes", 0)) for entry in diffs["added"])
    total_removed_compressed = sum(int(entry.get("Compressed_Size_Bytes", 0)) for entry in diffs["removed"])
    total_changed_compressed = sum(entry.get("Compressed_Diff", 0) for entry in diffs["changed"])
    total_added_uncompressed = sum(int(entry.get("Uncompressed_Size_Bytes", 0)) for entry in diffs["added"])
    total_removed_uncompressed = sum(int(entry.get("Uncompressed_Size_Bytes", 0)) for entry in diffs["removed"])
    total_changed_uncompressed = sum(entry.get("Uncompressed_Diff", 0) for entry in diffs["changed"])
    total_changed_sign = "+" if total_changed_compressed > 0 else "-"
    text += f"Total added: \n\t +{convert_to_human_readable_size(total_added_compressed)} (Compressed) "
    text += f"\n \t +{convert_to_human_readable_size(total_added_uncompressed)} (Uncompressed)\n"
    text += f"Total removed: \n\t -{convert_to_human_readable_size(total_removed_compressed)} (Compressed)"
    text += f"\n \t -{convert_to_human_readable_size(total_removed_uncompressed)} (Uncompressed)\n"
    text += f"Total changed: \n\t {total_changed_sign}"
    text += f"{convert_to_human_readable_size(abs(total_changed_compressed))} (Compressed) \n\t {total_changed_sign}"
    text += f"{convert_to_human_readable_size(abs(total_changed_uncompressed))} (Uncompressed)\n"
    text += "</details>\n"

    return text


def send_to_datadog(diffs, platform, python_version, compression, api_key):
    api_info = {"api_key": api_key, "site": "datadoghq.com"}
    message, tickets, prs = get_last_commit_data()
    timestamp = get_last_commit_timestamp()
    metrics = []

    for entry in diffs["unchanged"]:
        metrics.extend(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Compressed_Diff"))],
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:compressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:unchanged",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Uncompressed_Diff"))],
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:uncompressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:unchanged",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
        )
    for entry in diffs["changed"]:
        metrics.extend(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Compressed_Diff"))],
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:compressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:changed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Uncompressed_Diff"))],
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:uncompressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:changed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
        )
    for entry in diffs["added"]:
        metrics.extend(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Compressed_Size_Bytes"))],
                "size": entry.get("Compressed_Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:compressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:added",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Uncompressed_Size_Bytes"))],
                "size": entry.get("Uncompressed_Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:uncompressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:added",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
        )
    for entry in diffs["removed"]:
        metrics.extend(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Compressed_Size_Bytes"))],
                "size": entry.get("Compressed_Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:compressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:removed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Uncompressed_Size_Bytes"))],
                "size": entry.get("Uncompressed_Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    "compression:uncompressed",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:removed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            },
        )
    initialize(
        api_key=api_info["api_key"],
        api_host=f"https://api.{api_info['site']}",
    )

    api.Metric.send(metrics=metrics)


def main():
    parser = argparse.ArgumentParser(prog='gha_diff', allow_abbrev=False)
    parser.add_argument('--compressed-prev-sizes', required=True)
    parser.add_argument('--compressed-curr-sizes', required=True)
    parser.add_argument('--uncompressed-prev-sizes', required=True)
    parser.add_argument('--uncompressed-curr-sizes', required=True)
    parser.add_argument('--output', required=False)  # path to a file to export the diffs to
    parser.add_argument('--send-to-datadog', required=False)  # api key to send metrics to datadog
    parser.add_argument('--html-long-out', required=False)  # path to write long HTML output
    parser.add_argument('--html-short-out', required=False)  # path to write short HTML output
    parser.add_argument('--threshold', required=False)  # threshold for size increase
    args = parser.parse_args()

    with open(args.compressed_prev_sizes, "r") as f:
        prev_compressed_sizes = list(csv.DictReader(f))
        # prev_sizes = json.load(f)
    with open(args.compressed_curr_sizes, "r") as f:
        curr_compressed_sizes = json.load(f)
    with open(args.uncompressed_prev_sizes, "r") as f:
        prev_uncompressed_sizes = list(csv.DictReader(f))
    with open(args.uncompressed_curr_sizes, "r") as f:
        curr_uncompressed_sizes = json.load(f)

    diffs, platform, python_version = calculate_diffs(
        prev_compressed_sizes, curr_compressed_sizes, prev_uncompressed_sizes, curr_uncompressed_sizes
    )

    if args.send_to_datadog:
        send_to_datadog(diffs, platform, python_version, args.send_to_datadog)
    if args.output:
        with open(args.output, "w") as f:
            f.write(json.dumps(diffs, indent=2))

    # Always generate HTML output for the workflow
    long_text = display_diffs_to_html(diffs, platform, python_version)
    short_text = display_diffs_to_html_short(diffs, platform, python_version)

    if args.html_long_out:
        with open(args.html_long_out, "w") as f:
            f.write(long_text)
    if args.html_short_out:
        with open(args.html_short_out, "w") as f:
            f.write(short_text)

    # Check threshold if provided
    if args.threshold:
        threshold_value = int(args.threshold)
        if diffs['total_diff'] < threshold_value:
            print(f"Size increase does not exceed threshold of {args.threshold} bytes")
            return True
        else:
            print(f"Size increase exceeds threshold of {args.threshold} bytes")
            return False

    # No threshold specified, so it passes by default
    return True


if __name__ == "__main__":
    import sys

    result = main()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
