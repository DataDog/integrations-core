# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Bounded, non-redirecting intake transport. No instance HTTP credentials are used."""

from __future__ import annotations

import asyncio
import base64
import json
import random
import ssl
import time
from contextlib import suppress
from urllib.parse import unquote, urlsplit

from datadog_checks.base.utils.http import should_bypass_proxy

CONNECT_TIMEOUT = 10
SEND_STALL_TIMEOUT = 30
PAGE_TIMEOUT = 360
OTHER_TIMEOUT = 30
ABORT_TIMEOUT = 10
MAX_RESPONSE_BYTES = 65536


class UploadError(Exception):
    def __init__(self, code: str = "transport_error") -> None:
        self.code = code
        super().__init__(code)


class Intake:
    def __init__(self, delivery: dict, api_key: str, hostname: str, proxy: dict, trace: dict | None) -> None:
        self.url = urlsplit(delivery["baseUrl"].rstrip("/"))
        self.path = f"{self.url.path}/uploads/{delivery['uploadId']}"
        self.hostname = hostname
        self.headers = {"DD-API-KEY": api_key}
        if trace:
            self.headers.update(
                {
                    "x-datadog-trace-id": trace["traceId"],
                    "x-datadog-parent-id": trace["parentId"],
                    "x-datadog-sampling-priority": str(trace["samplingPriority"]),
                }
            )
        no_proxy = proxy.get("no_proxy") or []
        self.proxy = None
        if not should_bypass_proxy(delivery["baseUrl"], no_proxy):
            address = proxy.get(self.url.scheme)
            if address:
                self.proxy = urlsplit(address)
        # Always verify intake TLS, even if monitoring HTTP disables certificate verification.
        self.tls = ssl.create_default_context()

    async def request(
        self,
        method: str,
        suffix: str,
        body: bytes | memoryview = b"",
        headers: dict | None = None,
        *,
        deadline: float | None = None,
    ) -> None:
        failures = 0
        delay = 0.1
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError
            try:
                async with asyncio.timeout(PAGE_TIMEOUT if suffix.startswith("/pages/") else OTHER_TIMEOUT):
                    status, code = await self._attempt(method, suffix, body, headers or {})
                if status == 204:
                    return
                if status == 413 and code == "result_file_too_large" and suffix.startswith("/pages/"):
                    raise UploadError(code)
                if (status, code) not in ((503, "unavailable"), (500, "internal")):
                    raise UploadError(code)
            except (OSError, TimeoutError, asyncio.IncompleteReadError, ValueError):
                status, code = 0, "transport_error"
            # Provisional wire mapping: intake has no separate capacity code.
            if (status, code) != (503, "unavailable"):
                failures += 1
                if failures >= 5:
                    raise UploadError(code)
            await asyncio.sleep(random.uniform(delay / 2, delay))
            delay = min(5, delay * 2)

    async def _connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        host = self.url.hostname
        port = self.url.port or (443 if self.url.scheme == "https" else 80)
        async with asyncio.timeout(CONNECT_TIMEOUT):
            if not self.proxy:
                return await asyncio.open_connection(host, port, ssl=self.tls if self.url.scheme == "https" else None)
            proxy = self.proxy
            if proxy.scheme not in ("http", "https") or not proxy.hostname:
                raise UploadError("proxy_error")
            reader, writer = await asyncio.open_connection(
                proxy.hostname,
                proxy.port or (443 if proxy.scheme == "https" else 80),
                ssl=self.tls if proxy.scheme == "https" else None,
            )
            try:
                if self.url.scheme == "https":
                    authority = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
                    auth = self._proxy_auth()
                    request = f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n"
                    if auth:
                        request += f"Proxy-Authorization: {auth}\r\n"
                    writer.write((request + "\r\n").encode("ascii"))
                    await writer.drain()
                    status, _ = await self._read_headers(reader)
                    if status != 200:
                        raise UploadError("proxy_error")
                    await writer.start_tls(self.tls, server_hostname=host)
                return reader, writer
            except BaseException:
                writer.close()
                raise

    def _proxy_auth(self) -> str | None:
        if self.proxy and self.proxy.username is not None:
            credentials = f"{unquote(self.proxy.username)}:{unquote(self.proxy.password or '')}"
            return "Basic " + base64.b64encode(credentials.encode()).decode("ascii")
        return None

    async def _attempt(self, method: str, suffix: str, body: bytes | memoryview, headers: dict) -> tuple[int, str]:
        reader, writer = await self._connect()
        try:
            host = self.url.netloc
            path = self.path + suffix
            if self.proxy and self.url.scheme == "http":
                path = f"{self.url.scheme}://{host}{path}"
            fields = {
                "Host": host,
                "Connection": "close",
                "Content-Length": str(len(body)),
                "Content-Type": "text/csv" if method == "PUT" else "application/json",
                **self.headers,
                **headers,
            }
            if self.proxy and self.url.scheme == "http" and self._proxy_auth():
                fields["Proxy-Authorization"] = self._proxy_auth()
            if any("\r" in value or "\n" in value for value in fields.values()):
                raise UploadError("invalid_header")
            writer.write(
                (
                    f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in fields.items()) + "\r\n"
                ).encode()
            )
            await self._drain(writer)
            view = memoryview(body)
            for start in range(0, len(view), 65536):
                writer.write(view[start : start + 65536])
                await self._drain(writer)
            status, response_headers = await self._read_headers(reader)
            if status == 204:
                return status, ""
            # Error messages are never propagated; only known stable codes leave this transport.
            payload = bytearray()
            if response_headers.get("transfer-encoding", "").lower() == "chunked":
                while True:
                    size = int((await reader.readline()).split(b";", 1)[0], 16)
                    if size == 0:
                        break
                    if len(payload) + size > MAX_RESPONSE_BYTES:
                        raise UploadError("invalid_response")
                    payload.extend(await reader.readexactly(size))
                    if await reader.readexactly(2) != b"\r\n":
                        raise UploadError("invalid_response")
            else:
                size = int(response_headers.get("content-length", MAX_RESPONSE_BYTES + 1))
                if size > MAX_RESPONSE_BYTES or size < 0:
                    raise UploadError("invalid_response")
                payload.extend(await reader.readexactly(size))
            try:
                code = json.loads(payload)["error"]["code"]
            except (ValueError, TypeError, KeyError, RecursionError):
                code = "invalid_response"
            if not isinstance(code, str) or code not in {
                "invalid_argument",
                "unauthenticated",
                "not_found",
                "already_exists",
                "failed_precondition",
                "gone",
                "payload_too_large",
                "result_file_too_large",
                "scan_failed",
                "storage_access_denied",
                "unavailable",
                "internal",
            }:
                code = "invalid_response"
            return status, code
        finally:
            writer.close()

    @staticmethod
    async def _drain(writer: asyncio.StreamWriter) -> None:
        pending = asyncio.create_task(writer.drain())
        size = writer.transport.get_write_buffer_size()
        progress = time.monotonic()
        try:
            while not pending.done():
                await asyncio.wait((pending,), timeout=min(1, SEND_STALL_TIMEOUT / 4))
                current = writer.transport.get_write_buffer_size()
                now = time.monotonic()
                if current < size:
                    progress = now
                size = current
                # A slow but progressing send is not a stalled send.
                if not pending.done() and now - progress >= SEND_STALL_TIMEOUT:
                    raise TimeoutError
            await pending
        finally:
            if not pending.done():
                pending.cancel()
                with suppress(asyncio.CancelledError):
                    await pending

    @staticmethod
    async def _read_headers(reader: asyncio.StreamReader) -> tuple[int, dict[str, str]]:
        try:
            raw = await reader.readuntil(b"\r\n\r\n")
            if len(raw) > MAX_RESPONSE_BYTES:
                raise UploadError("invalid_response")
            lines = raw.decode("iso-8859-1").split("\r\n")
            status = int(lines[0].split()[1])
            fields = dict(line.split(":", 1) for line in lines[1:] if line)
            return status, {k.lower(): v.strip() for k, v in fields.items()}
        except (ValueError, IndexError, asyncio.LimitOverrunError):
            raise UploadError("invalid_response") from None
