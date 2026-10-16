import gzip
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from package_apw_assets import package


class PackageTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        # Fixture commits must not depend on the developer's signing key/hooks.
        self.git("config", "commit.gpgSign", "false")
        self.git("config", "core.hooksPath", "/dev/null")

    def git(self, *args: str) -> str:
        return (
            subprocess.check_output(["git", "-C", str(self.repo), *args])
            .decode()
            .strip()
        )

    def commit(self, files: dict[str, bytes]) -> str:
        for name, content in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Fixture")
        return self.git("rev-parse", "HEAD")

    def test_snapshot_is_repeatable_and_ignores_working_tree(self):
        commit = self.commit(
            {
                "example/assets/dashboard.json": b'{"title":"Committed dashboard"}',
                "example/manifest.json": b"{}",
            }
        )
        first = package(self.repo, commit, self.root / "first")

        (self.repo / "example/assets/dashboard.json").write_text(
            "uncommitted modification"
        )
        (self.repo / "example/assets/untracked.json").write_text("do not publish")
        second = package(self.repo, commit, self.root / "second")
        first_bytes = (self.root / "first/apw-assets.tar.gz").read_bytes()
        self.assertEqual(
            first_bytes, (self.root / "second/apw-assets.tar.gz").read_bytes()
        )
        self.assertEqual(first, second)
        self.assertEqual(first["commit"], commit)
        self.assertEqual(first["repository"], "DataDog/integrations-core")
        self.assertEqual(first["sha256"], hashlib.sha256(first_bytes).hexdigest())
        self.assertEqual(
            json.loads((self.root / "first/release.json").read_text()), first
        )
        self.assertEqual(
            (self.root / "first/SHA256SUMS").read_text(),
            f"{first['sha256']}  apw-assets.tar.gz\n",
        )
        with tarfile.open(fileobj=io.BytesIO(first_bytes), mode="r:gz") as archive:
            self.assertEqual(
                {member.name for member in archive if member.isfile()},
                {"repo/example/assets/dashboard.json", "repo/example/manifest.json"},
            )
            self.assertEqual(
                archive.extractfile("repo/example/assets/dashboard.json").read(),
                b'{"title":"Committed dashboard"}',
            )
        with self.assertRaises(FileExistsError):
            package(self.repo, commit, self.root / "first")
        for invalid in ["main", "HEAD", "abc123", "--output=bad"]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                package(self.repo, invalid, self.root / "invalid")

    def test_exports_complete_snapshot_including_new_asset_paths(self):
        self.commit(
            {
                "README.md": b"repository documentation",
                ".github/workflows/test.yml": b"workflow",
                "scripts/package.py": b"packaging code",
                "example/manifest.json": b"{}",
                "example/assets/dashboard.json": b"{}",
                "example/interfaces/example/config.md": b"interface",
                # New formats must ship without changing this producer.
                "example/future-format/definition.bin": bytes(range(256)),
                "example/future-format/.metadata": b"new format metadata",
                "example/tests/test_check.py": b"test code",
                "example/" + "long-name-" * 15 + ".json": b"{}",
                "example/images/screenshot with spaces.png": b"image",
            }
        )
        (self.repo / "scripts/package.py").chmod(0o755)
        (self.repo / "example/link.json").symlink_to("manifest.json")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Executable and symlink")
        commit = self.git("rev-parse", "HEAD")
        package(self.repo, commit, self.root / "snapshot")

        original = subprocess.check_output(
            [
                "git",
                "-C",
                str(self.repo),
                "archive",
                "--format=tar",
                "--prefix=repo/",
                commit,
            ]
        )
        with gzip.open(self.root / "snapshot/apw-assets.tar.gz", "rb") as archive:
            # Compare the entire tar stream, including headers and link records.
            self.assertEqual(archive.read(), original)

    def test_git_archive_failure_does_not_produce_a_release(self):
        self.commit({"README.md": b"repository documentation"})
        with self.assertRaises(subprocess.CalledProcessError):
            package(self.repo, "0" * 40, self.root / "failed")
        self.assertFalse((self.root / "failed/apw-assets.tar.gz").exists())
        self.assertFalse((self.root / "failed/release.json").exists())


if __name__ == "__main__":
    unittest.main()
