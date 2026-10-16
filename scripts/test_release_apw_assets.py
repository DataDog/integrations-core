import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from release_apw_assets import FILES, Release, api_get

COMMIT = "a" * 40
REPOSITORY = "DataDog/integrations-core"


class ReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.release = Release(REPOSITORY, COMMIT)
        archive = b"source snapshot"
        checksum = hashlib.sha256(archive).hexdigest()
        self.content = {
            FILES[0]: archive,
            "release.json": json.dumps(
                {
                    "format_version": 1,
                    "repository": REPOSITORY,
                    "commit": COMMIT,
                    "archive": FILES[0],
                    "sha256": checksum,
                }
            ).encode(),
            "SHA256SUMS": f"{checksum}  {FILES[0]}\n".encode(),
        }
        for name, content in self.content.items():
            (self.directory / name).write_bytes(content)
        self.remote = None
        self.ref = None
        self.mutations = []
        self.downloads = []
        self.fail_upload = None
        for target, replacement in [("api_get", self.api), ("gh", self.gh)]:
            mock = patch(f"release_apw_assets.{target}", side_effect=replacement)
            mock.start()
            self.addCleanup(mock.stop)
        env = patch.dict(
            "os.environ",
            {"GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"},
        )
        env.start()
        self.addCleanup(env.stop)

    def asset(self, name: str) -> dict[str, Any]:
        content = self.content[name]
        return {
            "id": FILES.index(name) + 1,
            "name": name,
            "state": "uploaded",
            "size": len(content),
            "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
        }

    def seed(self, *, draft: bool = False, files: tuple[str, ...] = FILES) -> None:
        self.remote = {
            "id": 42,
            "tag_name": self.release.tag,
            "target_commitish": COMMIT,
            "prerelease": True,
            "draft": draft,
            "assets": [self.asset(name) for name in files],
        }

    def api(self, endpoint: str, missing_ok: bool = False) -> dict[str, Any] | None:
        if "/git/ref/" in endpoint:
            return self.ref
        if "/tags/" in endpoint and (self.remote is None or self.remote["draft"]):
            return None
        return copy.deepcopy(self.remote)

    def gh(self, *args: str) -> bytes:
        if args[0] == "api":
            if "--paginate" in args:
                # Include an empty first page to exercise old draft recovery.
                return json.dumps([[], [self.remote] if self.remote else []]).encode()
            name = FILES[int(args[1].rsplit("/", 1)[1]) - 1]
            self.downloads.append(name)
            return self.content[name]
        command = args[1]
        if command == "view":
            return b'{"databaseId": 42}'
        self.mutations.append(args)
        if command == "create":
            self.assertIn("--draft", args)
            self.assertIn("--prerelease", args)
            self.assertIn("--latest=false", args)
            self.assertEqual(args[args.index("--target") + 1], COMMIT)
            self.seed(draft=True, files=())
        elif command == "upload":
            name = Path(args[3]).name
            self.assertTrue(self.remote["draft"])
            self.assertNotIn("--clobber", args)
            self.assertNotIn(name, [a["name"] for a in self.remote["assets"]])
            if self.fail_upload == name:
                raise subprocess.CalledProcessError(1, args)
            self.remote["assets"].append(self.asset(name))
        elif command == "edit":
            self.assertEqual({a["name"] for a in self.remote["assets"]}, set(FILES))
            self.assertIn("--draft=false", args)
            self.assertIn("--latest=false", args)
            self.remote["draft"] = False
        else:
            self.fail(f"unexpected mutation: {args}")
        return b""

    def test_unchanged_release_skips_without_downloading_archive_or_writing(self):
        self.seed()
        self.assertFalse(self.release.needs_package())
        self.assertEqual(self.downloads, ["release.json", "SHA256SUMS"])
        self.assertEqual(self.mutations, [])

    def test_missing_release_is_packaged_and_published_as_prerelease(self):
        self.assertTrue(self.release.needs_package())
        self.release.publish(self.directory)
        self.assertFalse(self.remote["draft"])
        self.assertEqual(
            [call[1] for call in self.mutations],
            ["create", "upload", "upload", "upload", "edit"],
        )

    def test_interrupted_upload_resumes_without_replacing_uploaded_assets(self):
        self.fail_upload = "release.json"
        with self.assertRaises(subprocess.CalledProcessError):
            self.release.publish(self.directory)
        self.assertTrue(self.remote["draft"])
        self.assertEqual([a["name"] for a in self.remote["assets"]], [FILES[0]])
        self.mutations.clear()
        self.fail_upload = None
        self.assertTrue(self.release.needs_package())
        self.release.publish(self.directory)
        self.assertEqual(
            [call[1] for call in self.mutations], ["upload", "upload", "edit"]
        )
        self.assertNotIn(
            FILES[0],
            [Path(call[3]).name for call in self.mutations if call[1] == "upload"],
        )

    def test_fully_uploaded_draft_only_needs_publication(self):
        self.seed(draft=True)
        self.release.publish(self.directory)
        self.assertEqual([call[1] for call in self.mutations], ["edit"])

    def test_publish_rerun_does_not_mutate_published_release(self):
        self.seed()
        self.release.publish(self.directory)
        self.assertEqual(self.mutations, [])

    def test_incomplete_published_release_fails_instead_of_skipping_or_repairing(self):
        self.seed(files=(FILES[0],))
        with self.assertRaises(ValueError):
            self.release.needs_package()
        with self.assertRaises(ValueError):
            self.release.publish(self.directory)
        self.assertEqual(self.mutations, [])

    def test_mismatched_uploads_are_never_replaced(self):
        for draft in [False, True]:
            with self.subTest(draft=draft):
                self.seed(draft=draft)
                self.remote["assets"][0]["digest"] = "sha256:" + "0" * 64
                with self.assertRaises(ValueError):
                    self.release.publish(self.directory)
                self.assertEqual(self.mutations, [])

    def test_invalid_release_state_fails_closed(self):
        mutations = [
            lambda r: r.update(target_commitish="b" * 40),
            lambda r: r.update(prerelease=False),
            lambda r: r["assets"][0].update(state="starter"),
            lambda r: r["assets"][0].update(size=0),
            lambda r: r["assets"][0].update(digest=None),
            lambda r: r["assets"].append(dict(r["assets"][0])),
            lambda r: r["assets"].append({"name": "unexpected"}),
        ]
        for mutate in mutations:
            self.seed()
            mutate(self.remote)
            with self.assertRaises(ValueError):
                self.release.needs_package()
            with self.assertRaises(ValueError):
                self.release.publish(self.directory)
            self.assertEqual(self.mutations, [])

    def test_wrong_metadata_identity_is_not_an_unchanged_success(self):
        metadata = json.loads(self.content["release.json"])
        metadata["commit"] = "b" * 40
        self.content["release.json"] = json.dumps(metadata).encode()
        self.seed()
        with self.assertRaises(ValueError):
            self.release.needs_package()
        self.assertEqual(self.mutations, [])

    def test_corrupt_local_archive_fails_before_writing(self):
        (self.directory / FILES[0]).write_bytes(b"corrupt snapshot")
        with self.assertRaises(ValueError):
            self.release.publish(self.directory)
        self.assertEqual(self.mutations, [])

    def test_existing_tag_pointing_elsewhere_is_rejected(self):
        self.ref = {"object": {"type": "commit", "sha": "b" * 40}}
        with self.assertRaises(ValueError):
            self.release.publish(self.directory)
        self.assertEqual(self.mutations, [])

    def test_invalid_commit_or_repository_is_rejected(self):
        for commit in ["main", "HEAD", "abc123", "--bad"]:
            with self.assertRaises(ValueError):
                Release(REPOSITORY, commit)
        with self.assertRaises(ValueError):
            Release("another/repository", COMMIT)


class APIErrorTest(unittest.TestCase):
    def test_only_explicit_404_means_missing(self):
        for status, code in [
            (200, 0),
            (404, 1),
            (401, 1),
            (403, 1),
            (429, 1),
            (500, 1),
        ]:
            with self.subTest(status=status):
                response = subprocess.CompletedProcess(
                    ["gh", "api"],
                    code,
                    stdout=f'HTTP/2.0 {status} Status\nHeader: value\n\n{{"id":42}}',
                    stderr="error" if code else "",
                )
                with patch("release_apw_assets.subprocess.run", return_value=response):
                    if status == 404:
                        self.assertIsNone(api_get("endpoint", missing_ok=True))
                    elif status == 200:
                        self.assertEqual(
                            api_get("endpoint", missing_ok=True), {"id": 42}
                        )
                    else:
                        with self.assertRaises(subprocess.CalledProcessError):
                            api_get("endpoint", missing_ok=True)

    def test_connection_error_is_not_missing(self):
        response = subprocess.CompletedProcess(
            ["gh", "api"], 1, stdout="", stderr="connection failed"
        )
        with patch("release_apw_assets.subprocess.run", return_value=response):
            with self.assertRaises(subprocess.CalledProcessError):
                api_get("endpoint", missing_ok=True)


if __name__ == "__main__":
    unittest.main()
