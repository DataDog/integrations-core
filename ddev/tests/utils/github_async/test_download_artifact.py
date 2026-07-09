"""download_artifact: redirect resolution, token non-leak, zip-slip, signed-URL failures."""

from __future__ import annotations

import httpx
import pytest

from ddev.utils.github_async import AsyncGitHubClient
from tests.utils.github_async.helpers import TOKEN, make_client, make_zip, patch_signed_download


async def test_download_artifact_token_not_leaked_to_redirect_target(monkeypatch, tmp_path) -> None:
    captured_signed_headers: dict[str, str] = {}

    def github_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Bearer ")
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        captured_signed_headers.update({k.lower(): v for k, v in request.headers.items()})
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    patch_signed_download(monkeypatch, signed_handler)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert "authorization" not in captured_signed_headers
    assert (tmp_path / "out" / "hello.txt").read_bytes() == b"hi"


async def test_download_artifact_non_302_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not a redirect")

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError, match="Expected 302"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.parametrize("status_code", [403, 503], ids=["forbidden", "server-error"])
async def test_download_artifact_signed_url_error_propagates(
    monkeypatch: pytest.MonkeyPatch, tmp_path, status_code: int
) -> None:
    """A failed signed-URL download propagates as httpx.HTTPStatusError (no retries)."""

    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=b"error")

    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


async def test_download_artifact_missing_location_header_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError, match="Missing Location"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.parametrize(
    "malicious_member",
    [
        pytest.param("../escape.txt", id="parent-traversal"),
        pytest.param("/etc/passwd", id="absolute-path"),
    ],
)
async def test_download_artifact_zip_slip_rejected(monkeypatch, tmp_path, malicious_member: str) -> None:
    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=make_zip({malicious_member: b"pwn"}))

    patch_signed_download(monkeypatch, signed_handler)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    dest = tmp_path / "out"
    with pytest.raises(ValueError, match="(?i)zip-slip"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", dest)

    # Nothing was extracted before the guard fired.
    assert list(dest.rglob("*")) == []
