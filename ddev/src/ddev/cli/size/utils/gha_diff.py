import argparse
import csv
import json

from ddev.cli.size.utils.common_funcs import convert_to_human_readable_size


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


def display_diffs_to_html(diffs, platform, python_version):
    sign = "+" if diffs['total_diff'] > 0 else ""
    text = f"<details><summary><h3>Size Delta for {platform} and Python {python_version}:\n"
    text += f"{sign}{convert_to_human_readable_size(diffs['total_diff'])}</h3></summary>\n\n"

    if diffs["added"]:
        text += "<details><summary>Added</summary>\n"
        text += "<table>\n"
        text += "<tr><th>Type</th><th>Name</th><th>Version</th><th>Size Delta</th></tr>\n"
        for entry in diffs["added"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = entry.get("Size", 0)
            typ = entry.get("Type", "")
            text += f"<tr><td>{typ}</td><td>{name}</td><td>{version}</td><td>+{size}</td></tr>\n"
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
    text = f"<details><summary><h3>Size Delta for {platform} and Python {python_version}:\n"
    text += f"{sign}{convert_to_human_readable_size(diffs['total_diff'])}</h3></summary>\n\n"
    total_added = sum(int(entry.get("Size_Bytes", 0)) for entry in diffs["added"])
    total_removed = sum(int(entry.get("Size_Bytes", 0)) for entry in diffs["removed"])
    total_changed = sum(entry.get("Diff", 0) for entry in diffs["changed"])

    text += f"Total added: {convert_to_human_readable_size(total_added)}\n"
    text += f"Total removed: -{convert_to_human_readable_size(total_removed)}\n"
    text += f"Total changed: {convert_to_human_readable_size(total_changed)}\n"
    text += "</details>\n"

    return text


# def send_to_datadog(diffs, platform, python_version, api_key):


def main():
    parser = argparse.ArgumentParser(prog='gha_diff', allow_abbrev=False)
    parser.add_argument('--prev-sizes', required=True)
    parser.add_argument('--curr-sizes', required=True)
    parser.add_argument('--output', required=False)  # path to a file to export the diffs to
    parser.add_argument('--send-to-datadog', action='store_true')
    parser.add_argument('--html-long-out', required=False)  # path to write long HTML output
    parser.add_argument('--html-short-out', required=False)  # path to write short HTML output
    args = parser.parse_args()

    with open(args.prev_sizes, "r") as f:
        prev_sizes = list(csv.DictReader(f))
        # prev_sizes = json.load(f)
    with open(args.curr_sizes, "r") as f:
        curr_sizes = json.load(f)

    diffs, platform, python_version = calculate_diffs(prev_sizes, curr_sizes)

    # if args.send_to_datadog:

    long_text = display_diffs_to_html(diffs, platform, python_version)
    short_text = display_diffs_to_html_short(diffs, platform, python_version)

    if args.html_long_out:
        with open(args.html_long_out, "w") as f:
            f.write(long_text)
    if args.html_short_out:
        with open(args.html_short_out, "w") as f:
            f.write(short_text)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json.dumps(diffs, indent=2))


if __name__ == "__main__":
    main()
