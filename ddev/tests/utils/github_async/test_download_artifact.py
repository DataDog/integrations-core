"""download_artifact: redirect resolution, token non-leak, zip-slip, signed-URL failures."""

from __future__ import annotations

import logging
import traceback

import httpx
import pytest

from ddev.utils.github_async import AsyncGitHubClient
from ddev.utils.github_errors import GitHubAuthenticationError
from tests.utils.github_async.helpers import TOKEN, make_client, make_zip, patch_signed_download

pytestmark = pytest.mark.usefixtures("instant_backoff")


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


async def test_download_artifact_authentication_error_remains_actionable(tmp_path) -> None:
    client = make_client(httpx.MockTransport(lambda request: httpx.Response(403)))

    with pytest.raises(GitHubAuthenticationError, match="ddev config set github.token"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.parametrize("status_code", [403, 503], ids=["forbidden", "server-error"])
async def test_download_artifact_signed_url_error_propagates(
    monkeypatch: pytest.MonkeyPatch, tmp_path, status_code: int
) -> None:
    """A signed-URL download that keeps failing reaches the caller once the retries are spent."""

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


async def test_an_expired_signed_url_is_resolved_again_rather_than_refetched(monkeypatch, tmp_path) -> None:
    """The signed URL is short-lived, so the retry has to start from the redirect.

    An expired URL comes back from the storage host as a 403. Retrying only the download would
    refetch the same dead URL and fail identically, so the pair is retried together and the second
    attempt asks GitHub for a fresh one.
    """
    signed_urls = ["https://signed.example/expired", "https://signed.example/fresh"]
    github_calls: list[httpx.Request] = []
    signed_calls: list[str] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_calls.append(request)
        return httpx.Response(302, headers={"location": signed_urls[min(len(github_calls) - 1, 1)]})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        signed_calls.append(url)
        if url.endswith("/expired"):
            return httpx.Response(403, content=b"<Error>AccessDenied</Error>")
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))

    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert len(github_calls) == 2
    assert signed_calls == ["https://signed.example/expired", "https://signed.example/fresh"]
    assert (tmp_path / "out" / "hello.txt").read_bytes() == b"hi"


async def test_a_denial_from_github_itself_is_not_retried_as_an_expired_url(tmp_path) -> None:
    """The 403 the artifact policy retries is the storage host's, not GitHub's.

    GitHub answers a real permission problem with its own 403, which arrives as an authentication
    error; retrying that would spend the whole ladder on a failure no wait can fix.
    """
    calls: list[httpx.Request] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(403)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))

    with pytest.raises(GitHubAuthenticationError):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert len(calls) == 1


# A signed URL keeps its signature in the query string. Both cases below assume the worst about what
# a failure quotes: a status whose httpx message is built from the full URL, and a transport error
# whose message happens to contain it. Neither is ours to control, so neither is relied upon.
SIGNATURE = "b1acc0dedb1acc0de"
SIGNED_URL = f"https://signed.example/zip?X-Amz-Expires=900&X-Amz-Signature={SIGNATURE}"

SIGNED_DOWNLOAD_FAILURES = [
    pytest.param(httpx.Response(403, content=b"<Error>AccessDenied</Error>"), id="expired-signature"),
    pytest.param(httpx.ConnectError(f"connection to {SIGNED_URL} refused"), id="transport-error"),
]


def _signed_download(failure: httpx.Response | Exception, *, fail_every_attempt: bool):
    """GitHub handler and signed handler where the signed download fails at least once."""
    github_calls: list[httpx.Request] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_calls.append(request)
        return httpx.Response(302, headers={"location": SIGNED_URL})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        if fail_every_attempt or len(github_calls) == 1:
            if isinstance(failure, Exception):
                raise failure
            return failure
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    return github_handler, signed_handler, github_calls


@pytest.mark.parametrize("failure", SIGNED_DOWNLOAD_FAILURES)
async def test_the_signed_url_credentials_never_reach_the_log(monkeypatch, tmp_path, caplog, failure) -> None:
    """A retry of the signed download must not write usable artifact credentials into CI logs.

    The retried exception reaches this client's log line and stamina's retry hook, both of which
    render it, and CI logs outlive the signature's validity.
    """
    github_handler, signed_handler, github_calls = _signed_download(failure, fail_every_attempt=False)
    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(
        token=TOKEN, transport=httpx.MockTransport(github_handler), logger=logging.getLogger("test-client")
    )

    with caplog.at_level(logging.WARNING):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    # The failure was retried, so there is a retry to have logged something.
    assert len(github_calls) == 2
    assert caplog.records
    # Messages and every structured field, since the signature can hide in either.
    logged = "\n".join(f"{record.getMessage()} {record.__dict__}" for record in caplog.records)
    assert SIGNATURE not in logged


@pytest.mark.parametrize("failure", SIGNED_DOWNLOAD_FAILURES)
async def test_the_signed_url_credentials_never_reach_the_error_that_escapes(monkeypatch, tmp_path, failure) -> None:
    """Once the retries are spent the failure reaches the caller, whose handler may log it.

    Python prints a chained cause in full, so the chain has to be as clean as the message.
    """
    github_handler, signed_handler, _ = _signed_download(failure, fail_every_attempt=True)
    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))

    with pytest.raises(httpx.HTTPError) as exc_info:
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    reported = "".join(traceback.format_exception(exc_info.value))
    assert SIGNATURE not in reported
