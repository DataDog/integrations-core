#!/usr/bin/env python3
"""Export a committed source snapshot; APW's consumer owns asset filtering."""

import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


def package(repository: Path, commit: str, output: Path) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full, lowercase Git SHA")
    output.mkdir(parents=True, exist_ok=False)
    archive_path = output / "apw-assets.tar.gz"
    # Read Git objects, never the working tree. Stream the complete archive so
    # large repositories do not have to fit in memory. Asset selection belongs
    # to APW: new asset types must not require updating every release producer.
    command = [
        "git",
        "-C",
        str(repository),
        "archive",
        "--format=tar",
        "--prefix=repo/",
        commit,
    ]
    with subprocess.Popen(command, stdout=subprocess.PIPE) as source:
        try:
            with (
                archive_path.open("wb") as raw,
                gzip.GzipFile(
                    filename="", mode="wb", fileobj=raw, mtime=0
                ) as compressed,
            ):
                shutil.copyfileobj(source.stdout, compressed)
            if source.wait():
                raise subprocess.CalledProcessError(source.returncode, command)
        except BaseException:
            # A write failure must not leave git blocked on a full pipe.
            source.kill()
            archive_path.unlink(missing_ok=True)
            raise
    with archive_path.open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    metadata = {
        "format_version": 1,
        "repository": "DataDog/integrations-core",
        "commit": commit,
        "archive": archive_path.name,
        "sha256": digest,
    }
    (output / "release.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(f"{digest}  {archive_path.name}\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(Path.cwd(), args.commit, args.output), indent=2))
