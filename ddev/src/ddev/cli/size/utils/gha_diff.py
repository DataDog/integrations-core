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


def calculate_diffs(prev_sizes, curr_sizes):
    def key(entry):
        return (
            entry.get("Name"),
            entry.get("Platform"),
            entry.get("Python_Version"),
            entry.get("Type"),
        )

    prev_map = {key(e): e for e in prev_sizes}
    curr_map = {key(e): e for e in curr_sizes}
    platform = curr_sizes[0]['Platform']
    python_version = curr_sizes[0]['Python_Version']

    added = []
    removed = []
    changed = []
    unchanged = []

    total_diff = 0
    # Find added and changed
    for curr_key, curr_entry in curr_map.items():
        if curr_key not in prev_map:
            added.append(curr_entry)
            total_diff += int(curr_entry.get("Size_Bytes", 0))
        else:
            prev_entry = prev_map[curr_key]
            prev_size = int(prev_entry.get("Size_Bytes", 0))
            curr_size = int(curr_entry.get("Size_Bytes", 0))
            if prev_size != curr_size:
                percentage = ((curr_size - prev_size) / prev_size) * 100 if prev_size != 0 else 0
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
                        "Diff": curr_size - prev_size,
                        "Percentage": percentage,
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
                        "Diff": 0,
                        "Percentage": 0,
                    }
                )
            total_diff += curr_size - prev_size
    # Find removed
    for prev_key, prev_entry in prev_map.items():
        if prev_key not in curr_map:
            removed.append(prev_entry)
            total_diff -= int(prev_entry.get("Size_Bytes", 0))

    return (
        {
            "added": order_by(added, "Size_Bytes"),
            "removed": order_by(removed, "Size_Bytes"),
            "changed": order_by(changed, "Percentage"),
            "total_diff": total_diff,
        },
        platform,
        python_version,
    )


def order_by(diffs, key):
    return sorted(diffs, key=lambda x: x[key], reverse=True)


def display_diffs(diffs, platform, python_version):
    sign = "+" if diffs['total_diff'] > 0 else ""
    print("=" * 52)
    print(f"Size Delta for {platform} and Python {python_version}")
    print("=" * 52)
    print(f"Total size difference: {sign}{convert_to_human_readable_size(diffs['total_diff'])}")
    print()

    if diffs["added"]:
        print("Added:")
        for entry in diffs["added"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = entry.get("Size", 0)
            typ = entry.get("Type", "")
            print(f"  + [{typ}] {name} {version}: +{size}")
        print()
    else:
        print("Added: None\n")

    if diffs["removed"]:
        print("Removed:")
        for entry in diffs["removed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = int(entry.get("Size_Bytes", 0))
            typ = entry.get("Type", "")
            print(f"  - [{typ}] {name} {version}: -{convert_to_human_readable_size(size)}")
        print()
    else:
        print("Removed: None\n")

    if diffs["changed"]:
        print("Changed:")
        for entry in diffs["changed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            typ = entry.get("Type", "")
            percentage = entry.get("Percentage", 0)
            diff = entry.get("Diff", 0)
            sign = "+" if diff > 0 else "-"
            version_diff = (
                f"{entry.get('Prev Version', version)} -> {entry.get('Version', version)}"
                if entry.get('Prev Version', version) != entry.get('Version', version)
                else version
            )
            print(
                f"  * [{typ}] {name} ({version_diff}): "
                f"{sign}{convert_to_human_readable_size(abs(diff))} ({sign}{percentage:.2f}%)"
            )
        print()
    else:
        print("Changed: None\n")
    print("=" * 60)


def display_diffs_to_html(diffs, uncompressed_diffs, platform, python_version):
    sign = "+" if diffs['total_diff'] > 0 else ""
    text = f"<details><summary><h4>Size Delta for {platform} and Python {python_version}:\n"
    text += f"{sign}{convert_to_human_readable_size(diffs['total_diff'])}</h4></summary>\n\n"

    if diffs["added"]:
        text += "<details><summary>Added</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th><th>Size Delta</th></tr>\n"
        for entry in diffs["added"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = entry.get("Size", 0)
            typ = entry.get("Type", "")
            text += f"<tr><td>{typ}</td><td>{name}</td><td>{version}</td><td>+{size}</td><td>+{size}</td></tr>\n"
        text += "</table>\n"
        text += "</details>\n\n"
    else:
        text += "No added dependencies/integrations\n\n"

    if diffs["removed"]:
        text += "<details><summary>Removed</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th><th>Size Delta</th></tr>\n"
        for entry in diffs["removed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = int(entry.get("Size_Bytes", 0))
            typ = entry.get("Type", "")
            text += f"<tr><td>{typ}</td><td>{name}</td>"
            text += f"<td>{version}</td><td>-{convert_to_human_readable_size(size)}</td></tr>\n"
        text += "</table>\n"
        text += "</details>\n\n"
    else:
        text += "No removed dependencies/integrations\n\n"

    if diffs["changed"]:
        text += "<details><summary>Changed</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th>"
        text += "<th>Size Delta</th><th>Percentage</th></tr>\n"
        for entry in diffs["changed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            typ = entry.get("Type", "")
            percentage = entry.get("Percentage", 0)
            diff = entry.get("Diff", 0)
            sign = "+" if diff > 0 else "-"
            version_diff = (
                f"{entry.get('Prev Version', version)} → {entry.get('Version', version)}"
                if entry.get('Prev Version', version) != entry.get('Version', version)
                else version
            )
            text += (
                f"<tr><td>{typ}</td><td>{name}</td><td>{version_diff}</td>"
                f"<td>{sign}{convert_to_human_readable_size(abs(diff))}</td>"
                f"<td>{sign}{percentage:.2f}%</td></tr>\n"
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
    total_added = sum(int(entry.get("Size_Bytes", 0)) for entry in diffs["added"])
    total_removed = sum(int(entry.get("Size_Bytes", 0)) for entry in diffs["removed"])
    total_changed = sum(entry.get("Diff", 0) for entry in diffs["changed"])
    total_changed_sign = "+" if total_changed > 0 else "-"
    text += f"Total added: +{convert_to_human_readable_size(total_added)}\n"
    text += f"Total removed: -{convert_to_human_readable_size(total_removed)}\n"
    text += f"Total changed: {total_changed_sign}{convert_to_human_readable_size(abs(total_changed))}\n"
    text += "</details>\n"

    return text


def send_to_datadog(diffs, platform, python_version, compression, api_key):
    api_info = {"api_key": api_key, "site": "datadoghq.com"}
    message, tickets, prs = get_last_commit_data()
    timestamp = get_last_commit_timestamp()

    metrics = []

    for entry in diffs["unchanged"]:
        metrics.append(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Diff"))],
                "size": entry.get("Diff"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    f"compression:{compression}",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:unchanged",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            }
        )
    for entry in diffs["changed"]:
        metrics.append(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Diff"))],
                "size": entry.get("Diff"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    f"compression:{compression}",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:changed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            }
        )
    for entry in diffs["added"]:
        metrics.append(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Size_Bytes"))],
                "size": entry.get("Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    f"compression:{compression}",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:added",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            }
        )
    for entry in diffs["removed"]:
        metrics.append(
            {
                "metric": f"{METRIC_NAME}.size_diff",
                "type": "gauge",
                "points": [(timestamp, entry.get("Size_Bytes"))],
                "size": entry.get("Size_Bytes"),
                "tags": [
                    f"name:{entry.get('Name')}",
                    f"type:{entry.get('Type')}",
                    f"name_type:{entry.get('Type')}({entry.get('Name')})",
                    f"python_version:{python_version}",
                    f"module_version:{entry.get('Version')}",
                    f"platform:{platform}",
                    "team:agent-integrations",
                    f"compression:{compression}",
                    f"metrics_version:{METRIC_VERSION}",
                    "diff_type:removed",
                    f"jira_ticket:{tickets[0]}",
                    f"pr_number:{prs[-1]}",
                ],
            }
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

    compressed_diffs, platform, python_version = calculate_diffs(prev_compressed_sizes, curr_compressed_sizes)
    uncompressed_diffs, platform, python_version = calculate_diffs(prev_uncompressed_sizes, curr_uncompressed_sizes)

    if args.send_to_datadog:
        send_to_datadog(compressed_diffs, platform, python_version, "compressed", args.send_to_datadog)
        send_to_datadog(uncompressed_diffs, platform, python_version, "uncompressed", args.send_to_datadog)

    long_text = display_diffs_to_html(compressed_diffs, uncompressed_diffs, platform, python_version)
    short_text = display_diffs_to_html_short(compressed_diffs, uncompressed_diffs, platform, python_version)

    if args.html_long_out:
        with open(args.html_long_out, "w") as f:
            f.write(long_text)
    if args.html_short_out:
        with open(args.html_short_out, "w") as f:
            f.write(short_text)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json.dumps({"compressed": compressed_diffs, "uncompressed": uncompressed_diffs}, indent=2))


if __name__ == "__main__":
    main()
