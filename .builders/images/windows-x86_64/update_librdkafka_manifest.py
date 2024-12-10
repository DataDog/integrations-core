import json
from argparse import ArgumentParser


def main(manifest_file, versions):
    with open(manifest_file) as f:
        manifest = json.load(f)

    for dep, version in versions.items():
        manifest.setdefault("overrides", []).append({
            "name": dep,
            "version": version,
        })

    with open(manifest_file, 'w') as f:
        json.dump(manifest, f)


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--set-version", action="append", required=True)

    args = ap.parse_args()
    main(args.file, dict(spec.split(':') for spec in args.set_version))
