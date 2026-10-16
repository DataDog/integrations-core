#!/usr/bin/env python3
"""Skip complete APW releases and resume matching draft uploads without clobbering."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

FILES = ("apw-assets.tar.gz", "release.json", "SHA256SUMS")


def gh(*args: str) -> bytes:
    return subprocess.check_output(["gh", *args])


def api_get(endpoint: str, missing_ok: bool = False) -> dict[str, Any] | None:
    # Only an explicit HTTP 404 means missing. Authentication, rate-limit and
    # network errors must stop the run instead of causing a publication attempt.
    result = subprocess.run(
        ["gh", "api", "--include", endpoint], capture_output=True, text=True
    )
    headers, _, body = result.stdout.partition("\n\n")
    status = headers.splitlines()[0] if headers else ""
    if missing_ok and re.fullmatch(r"HTTP/\S+ 404(?: .*)?", status):
        return None
    if result.returncode:
        print(result.stderr, file=sys.stderr, end="")
    result.check_returncode()
    return json.loads(body)


def digest(path: Path) -> str:
    with path.open("rb") as data:
        return "sha256:" + hashlib.file_digest(data, "sha256").hexdigest()


class Release:
    def __init__(self, repository: str, commit: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("commit must be a full, lowercase Git SHA")
        if repository != "DataDog/integrations-core":
            raise ValueError("this producer only publishes DataDog/integrations-core")
        self.repository = repository
        self.commit = commit
        self.tag = f"apw-assets-{commit}"
        self.endpoint = f"repos/{repository}/releases"

    def published(self) -> dict[str, Any] | None:
        return api_get(f"{self.endpoint}/tags/{self.tag}", missing_ok=True)

    def assets(self, release: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if (
            release["tag_name"] != self.tag
            or release["target_commitish"] != self.commit
            or not release["prerelease"]
        ):
            raise ValueError(
                "release identity does not match the expected APW snapshot"
            )
        assets = {asset["name"]: asset for asset in release["assets"]}
        if len(assets) != len(release["assets"]) or assets.keys() - set(FILES):
            raise ValueError(
                "release has unexpected or duplicate assets; inspect it manually"
            )
        for asset in assets.values():
            if asset["state"] != "uploaded" or asset["size"] <= 0:
                raise ValueError(
                    "release has an incomplete upload; inspect the draft manually"
                )
        return assets

    def validate_metadata(
        self, metadata: dict[str, Any], sums: str, archive_digest: str | None
    ) -> None:
        if (
            metadata.get("format_version") != 1
            or metadata.get("repository") != self.repository
            or metadata.get("commit") != self.commit
            or metadata.get("archive") != FILES[0]
            or not re.fullmatch(r"[0-9a-f]{64}", metadata.get("sha256", ""))
            or archive_digest != f"sha256:{metadata['sha256']}"
            or sums != f"{metadata['sha256']}  {FILES[0]}\n"
        ):
            raise ValueError(
                "release metadata/checksum does not match the expected snapshot"
            )

    def verify_published(self, release: dict[str, Any]) -> None:
        assets = self.assets(release)
        if release["draft"] or set(assets) != set(FILES):
            raise ValueError(
                "release is not complete and published; inspect it manually"
            )
        # Download only the two small manifests. GitHub's archive digest avoids
        # downloading the entire source snapshot on every unchanged cron tick.
        manifests = []
        for name in FILES[1:]:
            content = gh(
                "api",
                f"{self.endpoint}/assets/{assets[name]['id']}",
                "-H",
                "Accept: application/octet-stream",
            )
            if "sha256:" + hashlib.sha256(content).hexdigest() != assets[name].get(
                "digest"
            ):
                raise ValueError(f"GitHub digest mismatch for {name}")
            manifests.append(content)
        self.validate_metadata(
            json.loads(manifests[0]),
            manifests[1].decode(),
            assets[FILES[0]].get("digest"),
        )

    def needs_package(self) -> bool:
        release = self.published()
        if release is None or release["draft"]:
            return True
        self.verify_published(release)
        return False

    def publish(self, directory: Path) -> str:
        hashes = {name: digest(directory / name) for name in FILES}
        self.validate_metadata(
            json.loads((directory / "release.json").read_text()),
            (directory / "SHA256SUMS").read_text(),
            hashes[FILES[0]],
        )
        release = self.published()
        if release is None:
            # The tag endpoint only finds published releases. Include all pages
            # here so a failed draft from an older run can also be resumed.
            pages = json.loads(
                gh("api", "--paginate", "--slurp", f"{self.endpoint}?per_page=100")
            )
            matches = [r for page in pages for r in page if r["tag_name"] == self.tag]
            if len(matches) > 1:
                raise ValueError(
                    "multiple releases for the same tag; inspect them manually"
                )
            release = matches[0] if matches else None
        if release is None:
            # --target is ignored when a tag already exists; reject a tag that
            # points elsewhere before creating any release.
            ref = api_get(
                f"repos/{self.repository}/git/ref/tags/{self.tag}", missing_ok=True
            )
            if ref and (
                ref["object"]["type"] != "commit" or ref["object"]["sha"] != self.commit
            ):
                raise ValueError("existing tag does not point to the expected commit")
            notes = (
                f"APW source snapshot from {self.repository}@{self.commit}.\n"
                "Asset selection is performed by the downstream APW assembler.\n"
                "The uploaded apw-assets.tar.gz is the consumer input; GitHub's generated source archives are not used.\n"
                "Source identity and SHA-256 are recorded in release.json and SHA256SUMS.\n"
                f"Built by {os.environ['GITHUB_SERVER_URL']}/{self.repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}.\n"
            )
            gh(
                "release",
                "create",
                self.tag,
                "--target",
                self.commit,
                "--draft",
                "--prerelease",
                "--latest=false",
                "--title",
                f"APW assets {self.commit}",
                "--notes",
                notes,
            )
            # gh release view also finds drafts, unlike the REST tag endpoint.
            release_id = json.loads(
                gh("release", "view", self.tag, "--json", "databaseId")
            )["databaseId"]
            release = api_get(f"{self.endpoint}/{release_id}")
        assets = self.assets(release)
        # A retry may only keep identical completed uploads and add missing ones.
        # Never use --clobber or delete releases/assets, including draft assets.
        for name, asset in assets.items():
            if (
                asset.get("digest") != hashes[name]
                or asset["size"] != (directory / name).stat().st_size
            ):
                raise ValueError(
                    f"existing {name} differs from this build; inspect the release manually"
                )
        if not release["draft"]:
            self.verify_published(release)
            return "Already published; no files changed."
        for name in FILES:
            if name not in assets:
                gh("release", "upload", self.tag, str(directory / name))
        # Re-read the server state before exposing the draft to consumers.
        uploaded = self.assets(api_get(f"{self.endpoint}/{release['id']}"))
        if set(uploaded) != set(FILES) or any(
            uploaded[n].get("digest") != hashes[n] for n in FILES
        ):
            raise ValueError(
                "uploaded release does not match this build; leaving it unpublished"
            )
        gh("release", "edit", self.tag, "--draft=false", "--latest=false")
        self.verify_published(self.published())
        return "Published verified APW snapshot."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "publish"])
    parser.add_argument("--commit", required=True)
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    args = parser.parse_args()
    release = Release(os.environ["GH_REPO"], args.commit)
    if args.command == "check":
        needed = release.needs_package()
        print(f"package={str(needed).lower()}")
        message = (
            "Packaging needed."
            if needed
            else "Complete release exists; skipping packaging and publication."
        )
    else:
        message = release.publish(args.directory)
    print(f"{release.tag}: {message}", file=sys.stderr)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as output:
            output.write(f"{message}\n\nCommit: `{release.commit}`\n")
