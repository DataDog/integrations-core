# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Immutable APW source snapshots shared by public and private asset repositories."""

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _validate_identity(repository: str, commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full, lowercase Git SHA")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository):
        raise ValueError("repository must be an explicit GitHub owner/repository")


def package(source: Path, repository: str, commit: str, output: Path, excludes: tuple[str, ...] = ()) -> dict[str, Any]:
    _validate_identity(repository, commit)
    output.mkdir(parents=True, exist_ok=False)
    archive_path = output / "apw-assets.tar.gz"
    # Read Git objects, never the working tree. Stream the complete archive so
    # large repositories do not have to fit in memory. Asset selection belongs
    # to APW: new asset types must not require updating every release producer.
    command = [
        "git",
        "-C",
        str(source),
        "archive",
        "--format=tar",
        "--prefix=repo/",
        commit,
    ]
    if excludes:
        command.extend(["--", ".", *(f":(top,glob,exclude){pattern}" for pattern in excludes)])
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        try:
            assert process.stdout is not None
            with (
                archive_path.open("wb") as raw,
                gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
            ):
                shutil.copyfileobj(process.stdout, compressed)
            if process.wait():
                raise subprocess.CalledProcessError(process.returncode, command)
        except BaseException:
            # A write failure must not leave git blocked on a full pipe.
            process.kill()
            archive_path.unlink(missing_ok=True)
            raise
    with archive_path.open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    metadata = {
        "format_version": 1,
        "repository": repository,
        "commit": commit,
        "archive": archive_path.name,
        "sha256": digest,
    }
    (output / "release.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(f"{digest}  {archive_path.name}\n")
    return metadata


FILES = ("apw-assets.tar.gz", "release.json", "SHA256SUMS")


def gh(*args: str) -> bytes:
    return subprocess.check_output(["gh", *args])


def api_get(endpoint: str, missing_ok: bool = False) -> dict[str, Any] | None:
    # Only an explicit HTTP 404 means missing. Authentication, rate-limit and
    # network errors must stop the run instead of causing a publication attempt.
    result = subprocess.run(["gh", "api", "--include", endpoint], capture_output=True, text=True)
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
        _validate_identity(repository, commit)
        self.repository = repository
        self.commit = commit
        self.tag = f"apw-assets-{commit}"
        self.endpoint = f"repos/{repository}/releases"

    def published(self) -> dict[str, Any] | None:
        return api_get(f"{self.endpoint}/tags/{self.tag}", missing_ok=True)

    def tag_exists(self) -> bool:
        ref = api_get(f"repos/{self.repository}/git/ref/tags/{self.tag}", missing_ok=True)
        if ref and (ref["object"]["type"] != "commit" or ref["object"]["sha"] != self.commit):
            raise ValueError("existing tag does not point to the expected commit")
        return ref is not None

    def ensure_tag(self) -> str:
        """Create the source tag with a tag-authorized token, without moving existing tags."""
        if self.tag_exists():
            return "Source tag already exists at the expected commit."
        gh(
            "api",
            "--method",
            "POST",
            f"repos/{self.repository}/git/refs",
            "-f",
            f"ref=refs/tags/{self.tag}",
            "-f",
            f"sha={self.commit}",
        )
        return "Created source tag at the expected commit."

    def assets(self, release: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if release["tag_name"] != self.tag or release["target_commitish"] != self.commit or not release["prerelease"]:
            raise ValueError("release identity does not match the expected APW snapshot")
        assets = {asset["name"]: asset for asset in release["assets"]}
        if len(assets) != len(release["assets"]) or assets.keys() - set(FILES):
            raise ValueError("release has unexpected or duplicate assets; inspect it manually")
        for asset in assets.values():
            if asset["state"] != "uploaded" or asset["size"] <= 0:
                raise ValueError("release has an incomplete upload; inspect the draft manually")
        return assets

    def validate_metadata(self, metadata: dict[str, Any], sums: str, archive_digest: str | None) -> None:
        if (
            metadata.get("format_version") != 1
            or metadata.get("repository") != self.repository
            or metadata.get("commit") != self.commit
            or metadata.get("archive") != FILES[0]
            or not re.fullmatch(r"[0-9a-f]{64}", metadata.get("sha256", ""))
            or archive_digest != f"sha256:{metadata['sha256']}"
            or sums != f"{metadata['sha256']}  {FILES[0]}\n"
        ):
            raise ValueError("release metadata/checksum does not match the expected snapshot")

    def verify_published(self, release: dict[str, Any]) -> None:
        assets = self.assets(release)
        if release["draft"] or set(assets) != set(FILES):
            raise ValueError("release is not complete and published; inspect it manually")
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
            if "sha256:" + hashlib.sha256(content).hexdigest() != assets[name].get("digest"):
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

    def cleanup(self, retention_days: int = 7, *, dry_run: bool = False, now: datetime | None = None) -> str:
        """Remove expired APW releases, keeping the newest complete snapshot and this commit's release."""
        if retention_days < 1:
            raise ValueError("retention must be at least one day")
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
        pages = json.loads(gh("api", "--paginate", "--slurp", f"{self.endpoint}?per_page=100"))
        releases = []
        for page in pages:
            for release in page:
                match = re.fullmatch(r"apw-assets-([0-9a-f]{40})", release["tag_name"])
                if not match or release["draft"] or release.get("author", {}).get("login") != "github-actions[bot]":
                    continue
                try:
                    assets = Release(self.repository, match[1]).assets(release)
                except ValueError:
                    continue
                if set(assets) != set(FILES):
                    continue
                published = datetime.fromisoformat(release["published_at"])
                releases.append((published, release["id"], release))
        if not releases:
            return "No complete APW releases to clean up."
        newest_id = max(releases, key=lambda item: (item[0], item[1]))[1]
        count = total_bytes = 0
        for published, release_id, release in sorted(releases, key=lambda item: (item[0], item[1])):
            if published >= cutoff or release_id == newest_id or release["tag_name"] == self.tag:
                continue
            size = sum(asset["size"] for asset in release["assets"])
            if not dry_run:
                gh("api", "--method", "DELETE", f"{self.endpoint}/{release_id}")
            print(f"{'Would delete' if dry_run else 'Deleted'} {release['tag_name']} ({size} bytes); Git tag retained.")
            count += 1
            total_bytes += size
        return f"{'Would delete' if dry_run else 'Deleted'} {count} APW releases ({total_bytes} bytes)."

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
            pages = json.loads(gh("api", "--paginate", "--slurp", f"{self.endpoint}?per_page=100"))
            matches = [r for page in pages for r in page if r["tag_name"] == self.tag]
            if len(matches) > 1:
                raise ValueError("multiple releases for the same tag; inspect them manually")
            release = matches[0] if matches else None
        if release is None:
            # --target is ignored when a tag already exists; reject a tag that
            # points elsewhere before creating any release.
            self.tag_exists()
            notes = (
                f"APW source snapshot from {self.repository}@{self.commit}.\n"
                "Asset selection is performed by the downstream APW assembler.\n"
                "The uploaded apw-assets.tar.gz is the consumer input; "
                "GitHub's generated source archives are not used.\n"
                "Source identity and SHA-256 are recorded in release.json and SHA256SUMS.\n"
                f"Built by {os.environ['GITHUB_SERVER_URL']}/{self.repository}"
                f"/actions/runs/{os.environ['GITHUB_RUN_ID']}.\n"
            )
            gh(
                "release",
                "create",
                "--repo",
                self.repository,
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
            release_id = json.loads(gh("release", "view", self.tag, "--repo", self.repository, "--json", "databaseId"))[
                "databaseId"
            ]
            release = api_get(f"{self.endpoint}/{release_id}")
        assert release is not None
        assets = self.assets(release)
        # A retry may only keep identical completed uploads and add missing ones.
        # Never use --clobber or delete releases/assets, including draft assets.
        for name, asset in assets.items():
            if asset.get("digest") != hashes[name] or asset["size"] != (directory / name).stat().st_size:
                raise ValueError(f"existing {name} differs from this build; inspect the release manually")
        if not release["draft"]:
            self.verify_published(release)
            return "Already published; no files changed."
        for name in FILES:
            if name not in assets:
                gh("release", "upload", self.tag, str(directory / name), "--repo", self.repository)
        # Re-read the server state before exposing the draft to consumers.
        uploaded_release = api_get(f"{self.endpoint}/{release['id']}")
        assert uploaded_release is not None
        uploaded = self.assets(uploaded_release)
        if set(uploaded) != set(FILES) or any(uploaded[n].get("digest") != hashes[n] for n in FILES):
            raise ValueError("uploaded release does not match this build; leaving it unpublished")
        gh("release", "edit", self.tag, "--repo", self.repository, "--draft=false", "--latest=false")
        published = self.published()
        if published is None:
            raise ValueError("published release is not visible; retry verification")
        self.verify_published(published)
        return "Published verified APW snapshot."
