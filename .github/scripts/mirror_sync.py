# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Helpers for the nightly docker-image mirror sync."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def compute_new_upstream(old: dict, new: dict) -> list[tuple[str, str]]:
    """(image, tag) pairs that are newly-present AND not already mirrored."""
    def _pairs(manifest: dict) -> set[tuple[str, str]]:
        return {
            (entry['image'], tag)
            for entry in manifest.get('images', [])
            if not entry.get('mirrored', False)
            for tag in entry.get('tags', [])
        }

    added = _pairs(new) - _pairs(old)
    return sorted(added)


def _cmd_diff(args: argparse.Namespace) -> int:
    old_path = Path(args.old) if args.old else None
    old = json.loads(old_path.read_text()) if old_path and old_path.exists() else {'images': []}
    new = json.loads(Path(args.new).read_text())
    pairs = compute_new_upstream(old, new)
    payload = [{'image': image, 'tag': tag} for image, tag in pairs]
    Path(args.out).write_text(json.dumps(payload, indent=2) + '\n')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='mirror_sync')
    sub = parser.add_subparsers(dest='command', required=True)

    diff = sub.add_parser('diff')
    diff.add_argument('--old', required=True, help='Previous manifest JSON path')
    diff.add_argument('--new', required=True, help='New manifest JSON path')
    diff.add_argument('--out', required=True, help='Output path for new-upstream.json')
    diff.set_defaults(func=_cmd_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
