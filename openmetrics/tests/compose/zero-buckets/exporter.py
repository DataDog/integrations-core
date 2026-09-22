# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Deterministic, phase-controllable Prometheus exporter for the zero-bucket E2E tests.

The exporter serves one of two fixed counter snapshots ("baseline" and "update")
for four histogram families designed to exercise zero-bound histogram buckets
end to end:

- ``e2e_zero_all_zero_seconds``: every new observation between the two phases is
  exactly zero, so the whole delta lands in the ``le="0"`` bucket. This is the
  primary regression: the delta must reach the intake as a point-mass sketch at
  zero, not vanish because the bucket's lower bound became ``-Inf``.
- ``e2e_zero_mixed_seconds``: new observations land in ``(0, 5]`` while the
  ``le="0"`` bucket stays constant, proving the zero bucket is not reported as a
  zero-width bucket when it does not advance.
- ``e2e_zero_negative_seconds``: explicit negative thresholds precede the zero
  threshold, proving histograms with negative thresholds keep their existing
  decumulation.
- ``e2e_zero_big_count_seconds``: a large zero-bucket delta crossing 65,535 to
  verify large point-mass counts survive sketch aggregation.

Baselines are chosen so every bucket expected to emit a delta already has a
non-zero decumulated value in the baseline phase. The Agent suppresses the
first value it ever sees for a monotonic bucket context, and a bucket that is
zero on the baseline scrape is not tracked at all, so a zero baseline for a
bucket that later advances would silently swallow its first delta.

Control endpoints (all other paths return 404):

- ``GET /metrics``: exposition of the current phase.
- ``GET /control/set?phase=<name>``: atomically switch the current phase.
- ``GET /control/stats``: JSON ``{"phase": ..., "scrapes": N,
  "scrapes_by_phase": {...}}`` so tests can prove a phase was scraped before
  advancing.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ALL_ZERO = 'e2e_zero_all_zero_seconds'
MIXED = 'e2e_zero_mixed_seconds'
NEGATIVE = 'e2e_zero_negative_seconds'
BIG = 'e2e_zero_big_count_seconds'


def _histogram(name, help_text, buckets, count, total):
    lines = [f'# HELP {name} {help_text}', f'# TYPE {name} histogram']
    for le, value in buckets:
        lines.append(f'{name}_bucket{{le="{le}"}} {value}')
    lines.append(f'{name}_sum {total}')
    lines.append(f'{name}_count {count}')
    return lines


def _build_phases():
    baseline = []
    update = []

    # All-zero observations: 3 new requests, each 0s long.
    baseline.extend(_histogram(ALL_ZERO, 'All-zero request duration', [('0.0', 7), ('5.0', 7), ('+Inf', 7)], 7, 0))
    update.extend(_histogram(ALL_ZERO, 'All-zero request duration', [('0.0', 10), ('5.0', 10), ('+Inf', 10)], 10, 0))

    # Mixed observations: 3 new requests in (0, 5] (values 1, 1, 2), none zero.
    baseline.extend(_histogram(MIXED, 'Mixed request duration', [('0', 7), ('5', 10), ('+Inf', 10)], 10, 4))
    update.extend(_histogram(MIXED, 'Mixed request duration', [('0', 7), ('5', 13), ('+Inf', 13)], 13, 8))

    # Explicit negative thresholds: 2 old observations <= -5, 5 old in (-5, 0],
    # then 3 new requests in (0, 5] (values 1, 1, 2). The (0, 5] bucket starts
    # non-zero so its delta is not swallowed by first-value suppression.
    baseline.extend(
        _histogram(NEGATIVE, 'Mixed-sign request duration', [('-5.0', 2), ('0.0', 7), ('5.0', 10), ('+Inf', 10)], 10, 4)
    )
    update.extend(
        _histogram(NEGATIVE, 'Mixed-sign request duration', [('-5.0', 2), ('0.0', 7), ('5.0', 13), ('+Inf', 13)], 13, 8)
    )

    # Large all-zero delta: 65,600 new 0s observations, crossing 65,535.
    baseline.extend(
        _histogram(BIG, 'High-volume all-zero request duration', [('0', 100), ('5', 100), ('+Inf', 100)], 100, 0)
    )
    update.extend(
        _histogram(
            BIG, 'High-volume all-zero request duration', [('0', 65700), ('5', 65700), ('+Inf', 65700)], 65700, 0
        )
    )

    return {
        'baseline': '\n'.join(baseline) + '\n',
        'update': '\n'.join(update) + '\n',
    }


PHASES = _build_phases()
PROMETHEUS_CONTENT_TYPE = 'text/plain; version=0.0.4; charset=utf-8'


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.phase = 'baseline'
        self.scrapes_by_phase = dict.fromkeys(PHASES, 0)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/metrics':
            with STATE.lock:
                phase = STATE.phase
                STATE.scrapes_by_phase[phase] += 1
            self._send(200, PROMETHEUS_CONTENT_TYPE, PHASES[phase].encode('utf-8'))
        elif parsed.path == '/control/set':
            query = parse_qs(parsed.query)
            phase = (query.get('phase') or [''])[0]
            if phase not in PHASES:
                self._send(400, 'text/plain', f'unknown phase: {phase!r}'.encode('utf-8'))
                return
            with STATE.lock:
                STATE.phase = phase
            self._send(200, 'application/json', b'{"status": "ok"}')
        elif parsed.path == '/control/stats':
            with STATE.lock:
                payload = {
                    'phase': STATE.phase,
                    'scrapes': sum(STATE.scrapes_by_phase.values()),
                    'scrapes_by_phase': dict(STATE.scrapes_by_phase),
                }
            self._send(200, 'application/json', json.dumps(payload).encode('utf-8'))
        else:
            self._send(404, 'text/plain', b'not found')

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        print(f'{self.address_string()} {format % args}', flush=True)


STATE = State()

if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', 8999), Handler)
    print('Server is ready to receive web requests', flush=True)
    server.serve_forever()
