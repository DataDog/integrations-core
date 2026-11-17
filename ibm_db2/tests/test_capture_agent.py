# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import json
import runpy
import shutil
import subprocess
import zlib
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

CAPTURE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts' / 'capture_agent.py'))
pytestmark = pytest.mark.unit


@pytest.fixture
def recorder(tmp_path: Path) -> Iterator[tuple[ThreadingHTTPServer, Path]]:
    output = tmp_path / 'capture.jsonl'
    with CAPTURE['capture_server'](output, port=0) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            yield server, output
        finally:
            server.shutdown()
            thread.join(timeout=5)


def request(
    server: ThreadingHTTPServer, method: str, path: str, body: bytes = b'', encoding: str = ''
) -> tuple[int, bytes]:
    connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    try:
        connection.request(method, path, body, {'Content-Encoding': encoding, 'DD-API-KEY': 'HEADER_SECRET'})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


@pytest.mark.parametrize(
    'encoding',
    [
        '',
        'gzip',
        'deflate',
        pytest.param('zstd', marks=pytest.mark.skipif(shutil.which('zstd') is None, reason='zstd CLI required')),
    ],
)
def test_capture_compressed_batches(recorder: tuple[ThreadingHTTPServer, Path], encoding: str):
    """Compressed forwarder batches read back as individual events, including a successful idle snapshot."""
    server, output = recorder
    activity = [
        {'ddsource': 'ibm_db2', 'dbm_type': 'activity', 'ibm_db2_activity': [{'statement': 'SELECT ?'}]},
        {'ddsource': 'ibm_db2', 'dbm_type': 'activity', 'ibm_db2_activity': []},
    ]
    body = json.dumps(activity).encode()
    if encoding == 'gzip':
        body = gzip.compress(body)
    elif encoding == 'deflate':
        body = zlib.compress(body)
    elif encoding == 'zstd':
        body = subprocess.run(['zstd', '-cq'], input=body, capture_output=True, check=True).stdout

    status, _ = request(server, 'POST', '/api/v2/dbmactivity?api_key=QUERY_SECRET', body, encoding)
    assert status == 202
    assert list(CAPTURE['read_events'](output, 'dbm-activity')) == activity
    assert 'HEADER_SECRET' not in output.read_text()
    assert 'QUERY_SECRET' not in output.read_text()


def test_readback_separates_streams(recorder: tuple[ThreadingHTTPServer, Path]):
    """FQT in databasequery must not be mistaken for activity when selecting the acceptance stream."""
    server, output = recorder
    fqt = {'ddsource': 'ibm_db2', 'dbm_type': 'fqt', 'db': {'statement': 'SELECT ?'}}
    activity = {'ddsource': 'ibm_db2', 'dbm_type': 'activity', 'ibm_db2_activity': []}
    for path, event in (('/api/v2/databasequery', fqt), ('/api/v2/dbmactivity', activity)):
        assert request(server, 'POST', path, json.dumps([event]).encode())[0] == 202
    assert list(CAPTURE['read_events'](output, 'dbm-activity')) == [activity]
    assert list(CAPTURE['read_events'](output, 'dbm-samples')) == [fqt]


@pytest.mark.parametrize(
    'body, encoding', [(b'invalid', ''), (b'{}', ''), (b'[1]', ''), (b'invalid', 'gzip'), (b'[]', 'unknown')]
)
def test_invalid_request_is_not_acknowledged(recorder: tuple[ThreadingHTTPServer, Path], body: bytes, encoding: str):
    """Bad compression or batch shape must fail visibly instead of producing a misleading accepted capture."""
    server, output = recorder
    assert request(server, 'POST', '/api/v2/dbmactivity', body, encoding)[0] == 400
    assert not output.exists()


def test_agent_auxiliary_requests(recorder: tuple[ThreadingHTTPServer, Path]):
    """The Agent can validate its dummy key and flush non-DBM traffic without polluting DBM evidence."""
    server, output = recorder
    status, body = request(server, 'GET', '/api/v1/validate?api_key=QUERY_SECRET')
    assert status == 200
    assert json.loads(body) == {'valid': True}
    assert request(server, 'POST', '/api/v2/series', b'protobuf', 'zstd')[0] == 202
    assert not output.exists()


def test_readback_during_capture(tmp_path: Path):
    """Reading a growing file yields complete records without treating the in-progress final write as corruption."""
    output = tmp_path / 'capture.jsonl'
    first = {'ddsource': 'ibm_db2', 'timestamp': 1000}
    second = {'ddsource': 'ibm_db2', 'timestamp': 2000}
    records = [json.dumps({'path': '/api/v2/dbmactivity', 'events': [event]}) for event in (first, second)]
    output.write_text(records[0] + '\n' + records[1][:20])
    assert list(CAPTURE['read_events'](output, 'dbm-activity')) == [first]
    with output.open('a') as capture:
        capture.write(records[1][20:] + '\n')
    assert list(CAPTURE['read_events'](output, 'dbm-activity')) == [first, second]
