# Plan A: Python Discovery Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python discovery library to `datadog_checks_base` providing the `Service`/`Port` types, candidate-port iteration, HTTP/TCP probe helpers, and verifier predicates that integrations will use to implement `discover(service)` classmethods.

**Architecture:** Add new modules under the existing `datadog_checks_base/datadog_checks/base/utils/discovery/` package (alongside the existing `Discovery` class for intra-check item filtering, which is unrelated). All helpers are pure-Python, fully unit-testable without the Agent. The Agent-side bridge (Plan B) will populate `Service` instances from `listeners.Service`; until then, tests construct `Service` instances directly.

**Tech Stack:** Python (datadog_checks_base), pytest, mock, the standard library `requests` and `socket`.

**Spec:** [`docs/superpowers/specs/2026-05-06-advanced-autoconfig-discover-design.md`](../specs/2026-05-06-advanced-autoconfig-discover-design.md)

## File Structure

New files:
- `datadog_checks_base/datadog_checks/base/utils/discovery/service.py` — `Service` and `Port` dataclasses.
- `datadog_checks_base/datadog_checks/base/utils/discovery/ports.py` — `candidate_ports(service, hints)` iterator.
- `datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py` — predicate factories: `status_2xx`, `body_contains`, `body_matches`, `json_has`, `is_prometheus_exposition`, `response_equals`, `response_starts_with`.
- `datadog_checks_base/datadog_checks/base/utils/discovery/http.py` — `http_probe(host, port, path, *, verify, timeout=0.5)`.
- `datadog_checks_base/datadog_checks/base/utils/discovery/tcp.py` — `tcp_probe(host, port, *, send=b"", verify, timeout=0.5)`.
- `datadog_checks_base/tests/base/utils/discovery/test_service.py`
- `datadog_checks_base/tests/base/utils/discovery/test_ports.py`
- `datadog_checks_base/tests/base/utils/discovery/test_verifiers.py`
- `datadog_checks_base/tests/base/utils/discovery/test_http.py`
- `datadog_checks_base/tests/base/utils/discovery/test_tcp.py`

Modified:
- `datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi` — re-export the new public names.
- `datadog_checks_base/changelog.d/<PR>.added` — one-line changelog entry.

Existing files NOT modified:
- `discovery/discovery.py`, `discovery/cache.py`, `discovery/filter.py` — unrelated (intra-check item filtering); leave alone.

## Test command

All tests in this plan run via:

```bash
ddev --no-interactive test datadog_checks_base -- -k <pattern> -s
```

`-s` keeps stdout visible; `-k <pattern>` filters by test name. Without `-k`, the full base test suite runs — useful at the end of each task to confirm no regression.

---

### Task 1: `Service` and `Port` dataclasses

**Files:**
- Create: `datadog_checks_base/datadog_checks/base/utils/discovery/service.py`
- Create: `datadog_checks_base/tests/base/utils/discovery/test_service.py`

- [ ] **Step 1: Write failing tests**

`datadog_checks_base/tests/base/utils/discovery/test_service.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery.service import Port, Service


def test_port_defaults():
    p = Port(number=9090)
    assert p.number == 9090
    assert p.name == ""


def test_port_with_name():
    p = Port(number=9090, name="metrics")
    assert p.name == "metrics"


def test_port_is_hashable():
    {Port(9090), Port(9091, "metrics")}


def test_port_is_immutable():
    p = Port(9090)
    with pytest.raises(Exception):
        p.number = 9091  # type: ignore[misc]


def test_service_basic():
    svc = Service(id="docker://abc", host="10.0.0.1", ports=(Port(9090),))
    assert svc.id == "docker://abc"
    assert svc.host == "10.0.0.1"
    assert svc.ports == (Port(9090),)


def test_service_is_hashable():
    {Service(id="a", host="h", ports=(Port(1),))}


def test_service_ports_is_tuple_not_list():
    svc = Service(id="a", host="h", ports=(Port(1), Port(2)))
    assert isinstance(svc.ports, tuple)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_service -s
```

Expected: ImportError / ModuleNotFoundError on `discovery.service`.

- [ ] **Step 3: Implement the dataclasses**

`datadog_checks_base/datadog_checks/base/utils/discovery/service.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Port:
    number: int
    name: str = ""


@dataclass(frozen=True)
class Service:
    id: str
    host: str
    ports: tuple[Port, ...] = field(default_factory=tuple)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_service -s
```

Expected: PASS for all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/service.py \
        datadog_checks_base/tests/base/utils/discovery/test_service.py
git commit -m "datadog_checks_base: add Service and Port dataclasses for discovery"
```

---

### Task 2: `candidate_ports(service, hints)`

Iterates ports in this order: hint ports that the service actually exposes (in hint order), then remaining service ports in their original order. Skips duplicates. Hints not exposed by the service are skipped (not probed) — there's nothing to probe.

**Files:**
- Create: `datadog_checks_base/datadog_checks/base/utils/discovery/ports.py`
- Create: `datadog_checks_base/tests/base/utils/discovery/test_ports.py`

- [ ] **Step 1: Write failing tests**

`datadog_checks_base/tests/base/utils/discovery/test_ports.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery.ports import candidate_ports
from datadog_checks.base.utils.discovery.service import Port, Service


def _svc(*ports):
    return Service(id="x", host="h", ports=tuple(ports))


def test_hint_first_then_rest():
    svc = _svc(Port(8080), Port(9090), Port(80))
    assert list(candidate_ports(svc, [9090])) == [Port(9090), Port(8080), Port(80)]


def test_multiple_hints_in_order():
    svc = _svc(Port(80), Port(8080), Port(9090))
    assert list(candidate_ports(svc, [9090, 8080])) == [Port(9090), Port(8080), Port(80)]


def test_hint_not_exposed_skipped():
    svc = _svc(Port(80))
    assert list(candidate_ports(svc, [9090])) == [Port(80)]


def test_no_hints_returns_service_order():
    svc = _svc(Port(80), Port(9090))
    assert list(candidate_ports(svc, [])) == [Port(80), Port(9090)]


def test_no_ports_returns_empty():
    svc = _svc()
    assert list(candidate_ports(svc, [9090])) == []


def test_no_duplicates_when_hint_repeats():
    svc = _svc(Port(9090))
    assert list(candidate_ports(svc, [9090, 9090])) == [Port(9090)]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_ports -s
```

Expected: ImportError on `discovery.ports`.

- [ ] **Step 3: Implement**

`datadog_checks_base/datadog_checks/base/utils/discovery/ports.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable, Iterator

from .service import Port, Service


def candidate_ports(service: Service, hints: Iterable[int]) -> Iterator[Port]:
    """Yield ports to probe for a service, hint-first then remaining.

    Hints not exposed by the service are skipped; duplicates are collapsed.
    """
    by_number = {p.number: p for p in service.ports}
    seen: set[int] = set()
    for h in hints:
        if h in by_number and h not in seen:
            seen.add(h)
            yield by_number[h]
    for p in service.ports:
        if p.number not in seen:
            seen.add(p.number)
            yield p
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_ports -s
```

Expected: PASS for all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/ports.py \
        datadog_checks_base/tests/base/utils/discovery/test_ports.py
git commit -m "datadog_checks_base: add candidate_ports() for discovery probe ordering"
```

---

### Task 3: Verifier predicates

Each verifier is a factory that returns a predicate. HTTP verifiers are predicates over `requests.Response`; TCP verifiers are predicates over `bytes`. Predicate factories let the caller compose configuration at class-definition time (`DISCOVERY_VERIFY = body_contains("Total Accesses:")`).

**Files:**
- Create: `datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py`
- Create: `datadog_checks_base/tests/base/utils/discovery/test_verifiers.py`

- [ ] **Step 1: Write failing tests**

`datadog_checks_base/tests/base/utils/discovery/test_verifiers.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import Mock

import pytest

from datadog_checks.base.utils.discovery.verifiers import (
    body_contains,
    body_matches,
    is_prometheus_exposition,
    json_has,
    response_equals,
    response_starts_with,
    status_2xx,
)


def _resp(status=200, content_type="text/plain", body="", json_body=None):
    r = Mock()
    r.status_code = status
    r.headers = {"Content-Type": content_type}
    r.text = body
    if json_body is not None:
        r.json = Mock(return_value=json_body)
    else:
        r.json = Mock(side_effect=ValueError("not json"))
    return r


def test_status_2xx_pass():
    assert status_2xx()(_resp(status=200))
    assert status_2xx()(_resp(status=204))


def test_status_2xx_fail():
    assert not status_2xx()(_resp(status=301))
    assert not status_2xx()(_resp(status=500))


def test_body_contains_pass():
    assert body_contains("Total Accesses:")(_resp(body="Total Accesses: 42\n"))


def test_body_contains_fail_on_substring_absent():
    assert not body_contains("Total Accesses:")(_resp(body="something else"))


def test_body_contains_fail_on_non_2xx():
    assert not body_contains("anything")(_resp(status=500, body="anything"))


def test_body_matches_pass():
    assert body_matches(r"^Active connections:")(_resp(body="Active connections: 7\nblah"))


def test_body_matches_anchored_to_start_of_a_line_using_multiline_flag():
    # Demonstrates the convention: callers pass plain re patterns; we apply re.MULTILINE.
    assert body_matches(r"^server: nginx$")(_resp(body="HTTP/1.1 200 OK\nserver: nginx\n"))


def test_body_matches_fail():
    assert not body_matches(r"^Active connections:")(_resp(body="not nginx"))


def test_json_has_pass_top_level_keys():
    assert json_has(["version", "leader"])(_resp(json_body={"version": "1.7.0", "leader": "h1"}))


def test_json_has_fail_missing_key():
    assert not json_has(["version", "leader"])(_resp(json_body={"version": "1.7.0"}))


def test_json_has_fail_not_json():
    assert not json_has(["x"])(_resp(body="<html/>"))


def test_is_prometheus_exposition_pass_text_plain():
    body = "# HELP foo bar\nfoo 1\n"
    assert is_prometheus_exposition()(_resp(content_type="text/plain; version=0.0.4", body=body))


def test_is_prometheus_exposition_pass_openmetrics():
    body = "foo_total 42\n"
    assert is_prometheus_exposition()(_resp(content_type="application/openmetrics-text", body=body))


def test_is_prometheus_exposition_rejects_html():
    assert not is_prometheus_exposition()(_resp(content_type="text/html", body="<html/>"))


def test_is_prometheus_exposition_rejects_garbage_body():
    body = "this is not prometheus"
    assert not is_prometheus_exposition()(_resp(content_type="text/plain", body=body))


def test_response_equals_tcp_pass():
    assert response_equals(b"imok")(b"imok")


def test_response_equals_tcp_fail():
    assert not response_equals(b"imok")(b"imnotok")


def test_response_starts_with_tcp_pass():
    assert response_starts_with(b"+PONG")(b"+PONG\r\n")


def test_response_starts_with_tcp_fail():
    assert not response_starts_with(b"+PONG")(b"-ERR\r\n")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_verifiers -s
```

Expected: ImportError on `discovery.verifiers`.

- [ ] **Step 3: Implement the verifier predicates**

`datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Predicate factories for discovery probe verification.

Each public function returns a callable predicate. HTTP predicates take a
``requests.Response`` and return ``bool``. TCP predicates take ``bytes`` and
return ``bool``. The factory shape lets check classes declare verifiers as
class-level attributes, e.g. ``DISCOVERY_VERIFY = body_contains("Total Accesses:")``.
"""
import re
from collections.abc import Callable, Iterable

_PROM_LINE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+\S+")


HTTPPredicate = Callable[["requests.Response"], bool]  # noqa: F821 (forward ref for typing)
TCPPredicate = Callable[[bytes], bool]


def status_2xx() -> HTTPPredicate:
    def predicate(response) -> bool:
        return 200 <= response.status_code < 300
    return predicate


def body_contains(needle: str) -> HTTPPredicate:
    def predicate(response) -> bool:
        return 200 <= response.status_code < 300 and needle in response.text
    return predicate


def body_matches(pattern: str) -> HTTPPredicate:
    compiled = re.compile(pattern, re.MULTILINE)
    def predicate(response) -> bool:
        if not (200 <= response.status_code < 300):
            return False
        return bool(compiled.search(response.text))
    return predicate


def json_has(required_keys: Iterable[str]) -> HTTPPredicate:
    keys = tuple(required_keys)
    def predicate(response) -> bool:
        if not (200 <= response.status_code < 300):
            return False
        try:
            doc = response.json()
        except (ValueError, Exception):
            return False
        if not isinstance(doc, dict):
            return False
        return all(k in doc for k in keys)
    return predicate


def is_prometheus_exposition() -> HTTPPredicate:
    """Verify a Prometheus / OpenMetrics exposition response.

    Status must be 2xx, Content-Type must be text/plain or
    application/openmetrics-text, and at least one non-comment line must look
    like a Prometheus metric line.
    """
    def predicate(response) -> bool:
        if not (200 <= response.status_code < 300):
            return False
        ctype = response.headers.get("Content-Type", "").lower()
        if not (ctype.startswith("text/plain") or ctype.startswith("application/openmetrics-text")):
            return False
        for line in response.text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            return bool(_PROM_LINE.match(stripped))
        return False
    return predicate


def response_equals(expected: bytes) -> TCPPredicate:
    def predicate(buf: bytes) -> bool:
        return buf == expected
    return predicate


def response_starts_with(prefix: bytes) -> TCPPredicate:
    def predicate(buf: bytes) -> bool:
        return buf.startswith(prefix)
    return predicate
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_verifiers -s
```

Expected: PASS for all 17 tests.

- [ ] **Step 5: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py \
        datadog_checks_base/tests/base/utils/discovery/test_verifiers.py
git commit -m "datadog_checks_base: add verifier predicates for discovery probes"
```

---

### Task 4: `http_probe(host, port, path, *, verify, timeout=0.5)`

Performs a single GET request, swallows network errors as `False`, returns the predicate's verdict. IPv6 hosts are bracketed for URL use; the caller is expected to pass an already-bracketed host (the Agent-side bridge does this). The default timeout (500 ms) is the per-attempt budget.

**Files:**
- Create: `datadog_checks_base/datadog_checks/base/utils/discovery/http.py`
- Create: `datadog_checks_base/tests/base/utils/discovery/test_http.py`

- [ ] **Step 1: Write failing tests**

`datadog_checks_base/tests/base/utils/discovery/test_http.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import Mock, patch

import requests

from datadog_checks.base.utils.discovery.http import http_probe
from datadog_checks.base.utils.discovery.verifiers import body_contains, status_2xx


def _ok_response(body="ok", status=200, content_type="text/plain"):
    r = Mock()
    r.status_code = status
    r.text = body
    r.headers = {"Content-Type": content_type}
    return r


def test_http_probe_uses_correct_url_and_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("10.0.0.1", 9090, "/metrics", verify=status_2xx())
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://10.0.0.1:9090/metrics"
        assert kwargs["timeout"] == 0.5


def test_http_probe_passes_when_verify_passes():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response(body="Total Accesses: 42")
        assert http_probe("h", 80, "/server-status?auto", verify=body_contains("Total Accesses:"))


def test_http_probe_fails_when_verify_fails():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response(body="something else")
        assert not http_probe("h", 80, "/x", verify=body_contains("Total Accesses:"))


def test_http_probe_returns_false_on_connection_error():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError()
        assert not http_probe("h", 80, "/x", verify=status_2xx())


def test_http_probe_returns_false_on_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()
        assert not http_probe("h", 80, "/x", verify=status_2xx())


def test_http_probe_brackets_ipv6_in_url():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("[::1]", 80, "/x", verify=status_2xx())
        args, _ = mock_get.call_args
        assert args[0] == "http://[::1]:80/x"


def test_http_probe_custom_timeout():
    with patch("datadog_checks.base.utils.discovery.http.requests.get") as mock_get:
        mock_get.return_value = _ok_response()
        http_probe("h", 80, "/x", verify=status_2xx(), timeout=1.0)
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 1.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_http and discovery -s
```

Expected: ImportError on `discovery.http`.

- [ ] **Step 3: Implement**

`datadog_checks_base/datadog_checks/base/utils/discovery/http.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import requests


def http_probe(
    host: str,
    port: int,
    path: str,
    *,
    verify: Callable[[requests.Response], bool],
    timeout: float = 0.5,
) -> bool:
    """Perform a single GET probe and apply the verifier.

    Returns True iff the request completed and the verifier accepted the
    response. All network exceptions yield False (probes are best-effort).

    The ``host`` is used verbatim in the URL — IPv6 hosts must already be
    bracketed by the caller (the Agent-side bridge handles this).
    """
    url = f"http://{host}:{port}{path}"
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return False
    try:
        return bool(verify(response))
    finally:
        response.close()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_http and discovery -s
```

Expected: PASS for all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/http.py \
        datadog_checks_base/tests/base/utils/discovery/test_http.py
git commit -m "datadog_checks_base: add http_probe() for discovery"
```

---

### Task 5: `tcp_probe(host, port, *, send=b"", verify, timeout=0.5)`

Open a TCP socket, optionally send bytes, read up to `read_max` bytes (default 4096) within the timeout, apply the verifier. EOF is fine — verifier inspects whatever we got. All socket exceptions yield `False`.

**Files:**
- Create: `datadog_checks_base/datadog_checks/base/utils/discovery/tcp.py`
- Create: `datadog_checks_base/tests/base/utils/discovery/test_tcp.py`

- [ ] **Step 1: Write failing tests**

`datadog_checks_base/tests/base/utils/discovery/test_tcp.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
import threading
from contextlib import contextmanager

import pytest

from datadog_checks.base.utils.discovery.tcp import tcp_probe
from datadog_checks.base.utils.discovery.verifiers import (
    response_equals,
    response_starts_with,
)


@contextmanager
def _tcp_server(handler):
    """Run a one-shot TCP server on 127.0.0.1 and return its bound port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    done = threading.Event()

    def serve():
        try:
            conn, _ = sock.accept()
            try:
                handler(conn)
            finally:
                conn.close()
        except OSError:
            pass
        finally:
            done.set()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        sock.close()
        done.wait(timeout=1.0)


def test_tcp_probe_zookeeper_4lw_pattern():
    def handler(conn):
        data = conn.recv(64)
        if data == b"ruok":
            conn.sendall(b"imok")
    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port, send=b"ruok",
                         verify=response_equals(b"imok"), timeout=1.0)


def test_tcp_probe_redis_ping_pattern():
    def handler(conn):
        conn.recv(64)
        conn.sendall(b"+PONG\r\n")
    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port, send=b"PING\r\n",
                         verify=response_starts_with(b"+PONG"), timeout=1.0)


def test_tcp_probe_server_speaks_first():
    def handler(conn):
        conn.sendall(b'{"service":"nutcracker","source":"x","version":"0.5"}')
    with _tcp_server(handler) as port:
        assert tcp_probe("127.0.0.1", port,
                         verify=response_starts_with(b'{"service":"nutcracker"'),
                         timeout=1.0)


def test_tcp_probe_returns_false_when_verifier_rejects():
    def handler(conn):
        conn.sendall(b"WRONG")
    with _tcp_server(handler) as port:
        assert not tcp_probe("127.0.0.1", port,
                             verify=response_starts_with(b"+PONG"), timeout=1.0)


def test_tcp_probe_returns_false_on_refused_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # port is now free; nothing listening
    assert not tcp_probe("127.0.0.1", port,
                         verify=response_starts_with(b"x"), timeout=1.0)


def test_tcp_probe_returns_false_on_timeout():
    def handler(conn):
        # Stall: never send anything, never close (until the test releases us).
        import time
        time.sleep(2.0)
    with _tcp_server(handler) as port:
        assert not tcp_probe("127.0.0.1", port,
                             verify=response_starts_with(b"x"), timeout=0.1)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_tcp and discovery -s
```

Expected: ImportError on `discovery.tcp`.

- [ ] **Step 3: Implement**

`datadog_checks_base/datadog_checks/base/utils/discovery/tcp.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
from collections.abc import Callable

_DEFAULT_READ_MAX = 4096


def tcp_probe(
    host: str,
    port: int,
    *,
    send: bytes = b"",
    verify: Callable[[bytes], bool],
    timeout: float = 0.5,
    read_max: int = _DEFAULT_READ_MAX,
) -> bool:
    """Open a TCP connection, optionally send bytes, read up to ``read_max``,
    and apply the verifier.

    Returns True iff the connection succeeded and the verifier accepted the
    bytes received within the timeout. All socket errors yield False.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if send:
                sock.sendall(send)
            chunks: list[bytes] = []
            remaining = read_max
            while remaining > 0:
                try:
                    chunk = sock.recv(min(4096, remaining))
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            buf = b"".join(chunks)
    except OSError:
        return False
    return bool(verify(buf))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_tcp and discovery -s
```

Expected: PASS for all 6 tests. (The timeout test runs for ~0.1 s; the stall server is left to die when the test releases its enclosing context.)

- [ ] **Step 5: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/tcp.py \
        datadog_checks_base/tests/base/utils/discovery/test_tcp.py
git commit -m "datadog_checks_base: add tcp_probe() for discovery"
```

---

### Task 6: Re-export the new public names from `discovery.__init__`

The existing `__init__.py` uses `lazy_loader.attach_stub`, which means exports are declared in `__init__.pyi`.

**Files:**
- Modify: `datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi`

- [ ] **Step 1: Read the current stub**

```bash
cat datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi
```

Expected current content:

```python
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .discovery import Discovery

__all__ = ['Discovery']
```

- [ ] **Step 2: Write a failing import test**

`datadog_checks_base/tests/base/utils/discovery/test_exports.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def test_public_exports():
    from datadog_checks.base.utils import discovery

    expected = {
        "Discovery",
        "Service",
        "Port",
        "candidate_ports",
        "http_probe",
        "tcp_probe",
        "status_2xx",
        "body_contains",
        "body_matches",
        "json_has",
        "is_prometheus_exposition",
        "response_equals",
        "response_starts_with",
    }
    assert expected.issubset(set(dir(discovery)))
```

```bash
ddev --no-interactive test datadog_checks_base -- -k test_public_exports -s
```

Expected: FAIL — only `Discovery` exported.

- [ ] **Step 3: Update the stub**

Replace `datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi` with:

```python
# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .discovery import Discovery
from .http import http_probe
from .ports import candidate_ports
from .service import Port, Service
from .tcp import tcp_probe
from .verifiers import (
    body_contains,
    body_matches,
    is_prometheus_exposition,
    json_has,
    response_equals,
    response_starts_with,
    status_2xx,
)

__all__ = [
    'Discovery',
    'Port',
    'Service',
    'body_contains',
    'body_matches',
    'candidate_ports',
    'http_probe',
    'is_prometheus_exposition',
    'json_has',
    'response_equals',
    'response_starts_with',
    'status_2xx',
    'tcp_probe',
]
```

- [ ] **Step 4: Run the test**

```bash
ddev --no-interactive test datadog_checks_base -- -k test_public_exports -s
```

Expected: PASS.

- [ ] **Step 5: Run the full discovery test suite to confirm nothing regressed**

```bash
ddev --no-interactive test datadog_checks_base -- -k discovery -s
```

Expected: all tests from Tasks 1–5 plus the existing `test_discovery.py` tests pass.

- [ ] **Step 6: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi \
        datadog_checks_base/tests/base/utils/discovery/test_exports.py
git commit -m "datadog_checks_base: export discovery probe helpers"
```

---

### Task 7: Changelog entry

Per `CLAUDE.md` in this repo: changelogs MUST be created via `ddev release changelog new`, never edited by hand.

**Files:**
- Create: `datadog_checks_base/changelog.d/<PR_NUMBER>.added` (created by the command).

- [ ] **Step 1: Add the entry**

The PR number isn't known yet — placeholder is the GitHub PR number once the branch is pushed and the PR opened. Until then, use `0` and rename later, or add it after opening the PR.

```bash
ddev release changelog new added datadog_checks_base \
  -m "Add Service/Port types and probe helpers (http_probe, tcp_probe, candidate_ports, verifier predicates) under datadog_checks.base.utils.discovery for advanced auto-config."
```

- [ ] **Step 2: Verify the file appeared**

```bash
ls datadog_checks_base/changelog.d/*.added | head -1
```

Expected: a new `<N>.added` file.

- [ ] **Step 3: Commit**

```bash
git add datadog_checks_base/changelog.d/*.added
git commit -m "datadog_checks_base: changelog entry for discovery probe helpers"
```

---

### Task 8: Whole-suite confidence run

A final unfiltered run to confirm no regression elsewhere in `datadog_checks_base`.

- [ ] **Step 1: Format**

```bash
ddev test -fs datadog_checks_base
```

Expected: clean / formats applied if needed.

- [ ] **Step 2: Run the full base test suite**

```bash
ddev --no-interactive test datadog_checks_base
```

Expected: all tests pass. New tests from Tasks 1–6 are included; existing tests (including `test_discovery.py` for the unrelated `Discovery` class) are unaffected.

- [ ] **Step 3: If formatting changed anything, commit**

```bash
git status
# if there are formatting fixups:
git add -p
git commit -m "datadog_checks_base: apply formatter to discovery helpers"
```

---

## Self-Review

**Spec coverage:**
- `Service` / `Port` types crossed into Python — Task 1.
- Helpers `http_probe`, `tcp_probe`, `candidate_ports`, verifiers — Tasks 2–5.
- Public re-export — Task 6.
- Changelog — Task 7.
- Full-suite confidence — Task 8.

NOT covered by this plan (intentionally — they belong to Plan B and Plan C):
- Per-pattern base classes (`OpenMetrics` discovery mixin, `HTTPStaticDiscoverable`, `TCPDiscoverable`, etc.). These are deferred until the rtloader bridge in Plan B exists, because the base-class tests need a `Service` shape that crosses cleanly between Python tests and the Go bridge. Doing them in Plan A risks designing the surface twice. The helpers in this plan are sufficient for any per-integration `discover()` to be written by hand.
- Any per-integration `discover()` method. Plan C.
- Agent-side rtloader bridge, `discoverer` package, `configmgr` integration, krakend artifact removal. Plan B.

**Placeholder scan:** No `TBD`, `TODO`, `implement later`, or "similar to Task N" references. Each step shows the actual code or command.

**Type consistency:**
- `Service.ports` is `tuple[Port, ...]` everywhere it appears.
- `Port` constructor: `Port(number, name="")` — Task 1 defines, Tasks 2–5 use consistently.
- `candidate_ports(service, hints) -> Iterator[Port]` — Task 2 defines, downstream tasks (in Plan C) will iterate the result.
- `http_probe(host, port, path, *, verify, timeout=0.5) -> bool` — matches the spec verbatim.
- `tcp_probe(host, port, *, send=b"", verify, timeout=0.5, read_max=4096) -> bool` — adds `read_max` as a kwarg with a documented default; spec mentions `read_max: 4096` in the YAML form discussion, harmless to surface as a kwarg.
- Verifier names match the spec: `is_prometheus_exposition`, `status_2xx`, `body_contains`, `body_matches`, `json_has`, `response_equals`, `response_starts_with`.

**Scope:** This plan is one-PR-sized: ~5 small modules, ~5 small test files, one changelog entry. No cross-repo dependencies. Plan B and Plan C will follow.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-06-discover-python-library.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks. Fast iteration; good for plans with many small tasks like this one.
2. **Inline Execution** — Execute tasks in this session via executing-plans. Batch with checkpoints for review.

Which approach?
