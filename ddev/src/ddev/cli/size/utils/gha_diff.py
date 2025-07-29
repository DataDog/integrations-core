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

    print(prev_sizes)

    prev_map = {key(e): e for e in prev_sizes}
    curr_map = {key(e): e for e in curr_sizes}

    added = []
    removed = []
    changed = []

    total_diff = 0
    # Find added and changed
    for curr_key, curr_entry in curr_map.items():
        if curr_key not in prev_map:
            added.append(curr_entry)
            total_diff += curr_entry.get("Size_Bytes", 0)
        else:
            prev_entry = prev_map[curr_key]
            prev_size = prev_entry.get("Size_Bytes", 0)
            curr_size = curr_entry.get("Size_Bytes", 0)
            if prev_size != curr_size:
                changed.append(
                    {
                        "Name": curr_entry.get("Name"),
                        "Version": curr_entry.get("Version"),
                        "Prev Version": prev_entry.get("Version"),
                        "Platform": curr_entry.get("Platform"),
                        "Python_Version": curr_entry.get("Python_Version"),
                        "Type": curr_entry.get("Type"),
                        "prev_Size_Bytes": prev_size,
                        "curr_Size_Bytes": curr_size,
                        "diff": curr_size - prev_size,
                    }
                )
            total_diff += curr_size - prev_size
    # Find removed
    for prev_key, prev_entry in prev_map.items():
        if prev_key not in curr_map:
            removed.append(prev_entry)
            total_diff -= prev_entry.get("Size_Bytes", 0)

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "total_diff": total_diff,
    }


def display_diffs(diffs):
    # Print a well-formatted summary of the diffs
    sign = "+" if diffs['total_diff'] > 0 else "-"
    print("=" * 60)
    print(
        f"Dependency Size Differences for {diffs['added'][0]['Platform']} and"
        f" Python {diffs['added'][0]['Python_Version']}"
    )
    print("=" * 60)
    print(f"Total size difference: {sign}{convert_to_human_readable_size(diffs['total_diff'])}")
    print()

    if diffs["added"]:
        print("Added:")
        for entry in diffs["added"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = entry.get("Size", 0)
            typ = entry.get("Type", "")
            print(f"  + [{typ}] {name} {version}: + {size}")
        print()
    else:
        print("Added: None\n")

    if diffs["removed"]:
        print("Removed:")
        for entry in diffs["removed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            size = entry.get("Size", 0)
            typ = entry.get("Type", "")
            print(f"  - [{typ}] {name} {version}: - {size}")
        print()
    else:
        print("Removed: None\n")

    if diffs["changed"]:
        print("Changed:")
        for entry in diffs["changed"]:
            name = entry.get("Name", "")
            version = entry.get("Version", "")
            typ = entry.get("Type", "")
            prev_size = entry.get("prev_Size_Bytes", 0)
            # curr_size = entry.get("curr_Size_Bytes", 0)
            diff = entry.get("diff", 0)
            percentage = (diff / prev_size) * 100 if prev_size != 0 else 0
            sign = "+" if diff > 0 else "-"
            version_diff = (
                f"{entry.get('Prev Version', version)} -> {entry.get('Version', version)} "
                if entry.get('Prev Version', version) != entry.get('Version', version)
                else "version unchanged"
            )
            print(
                f"  * [{typ}] {name} {version_diff}: "
                f"{sign} {convert_to_human_readable_size(diff)} ({sign}{percentage:.2f}%)"
            )
        print()
    else:
        print("Changed: None\n")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(prog='gha_diff', allow_abbrev=False)
    parser.add_argument('--prev-sizes', required=True)
    parser.add_argument('--curr-sizes', required=True)
    args = parser.parse_args()

    with open(args.prev_sizes, "r") as f:
        prev_sizes = list(csv.DictReader(f))
        # prev_sizes = json.load(f)
    with open(args.curr_sizes, "r") as f:
        curr_sizes = json.load(f)

    # prev_sizes = [
    #     {
    #         "Name": "cryptography",
    #         "Version": "45.0.5",
    #         "Size_Bytes": 21933835,
    #         "Size": "20.92 MB",
    #         "Type": "Dependency",
    #         "Platform": "macos-x86_64",
    #         "Python_Version": "3.12",
    #     },
    #     {
    #         "Name": "PyYAML",
    #         "Version": "6.0.1",
    #         "Size_Bytes": 1234567,
    #         "Size": "1.18 MB",
    #         "Type": "Dependency",
    #         "Platform": "macos-x86_64",
    #         "Python_Version": "3.12",
    #     },
    #     {
    #         "Name": "hola",
    #         "Version": "3.9.10",
    #         "Size_Bytes": 2345678,
    #         "Size": "2.24 MB",
    #         "Type": "Dependency",
    #     },
    # ]

    # curr_sizes = [
    #     {
    #         "Name": "cryptography",
    #         "Version": "45.0.6",
    #         "Size_Bytes": 22933835,  # Increased size
    #         "Size": "21.88 MB",
    #         "Type": "Dependency",
    #         "Platform": "macos-x86_64",
    #         "Python_Version": "3.12",
    #     },
    #     {
    #         "Name": "PyYAML",
    #         "Version": "6.0.1",
    #         "Size_Bytes": 1234567,
    #         "Size": "1.18 MB",
    #         "Type": "Dependency",
    #         "Platform": "macos-x86_64",
    #         "Python_Version": "3.12",
    #     },
    #     {
    #         "Name": "orjson",
    #         "Version": "3.9.10",
    #         "Size_Bytes": 2345678,
    #         "Size": "2.24 MB",
    #         "Type": "Dependency",
    #         "Platform": "macos-x86_64",
    #         "Python_Version": "3.12",
    #     },
    # ]

    diffs = calculate_diffs(prev_sizes, curr_sizes)

    display_diffs(diffs)


if __name__ == "__main__":
    main()
