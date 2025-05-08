import argparse
from modes import status_mode


def main():
    parser = argparse.ArgumentParser(description="Package Size Analyzer CLI")

    # Define allowed choices
    valid_modes = ["status", "diff", "timeline"]
    valid_platforms = ["linux-aarch64", "linux-x86_64", "macos-x86_64", "windows-x86_64"]
    valid_python_versions = ["3.12"]

    # Arguments
    parser.add_argument("mode", choices=valid_modes, help="Mode of operation")
    parser.add_argument("--platform", choices=valid_platforms, required=False, help="Target platform")
    parser.add_argument("--python", choices=valid_python_versions, required=False, help="Python version (MAJOR.MINOR)")
    parser.add_argument("--compressed", action="store_true", help="Measure compressed size")

    args = parser.parse_args()

    # Execute the corresponding function based on the selected mode
    if args.mode == "status":
        # if an argument is not specified, all possibilities are executed
        if args.platform is None and args.python is None:
            for platform in valid_platforms:
                for version in valid_python_versions:
                    status_mode(platform, version, args.compressed)
        elif args.platform is None:
            for platform in valid_platforms:
                status_mode(platform, args.python, args.compressed)
        elif args.python is None:
            for version in valid_python_versions:
                status_mode(args.platform, version, args.compressed)
        else:
            status_mode(args.platform, args.python, args.compressed)

if __name__ == "__main__":
    main()
