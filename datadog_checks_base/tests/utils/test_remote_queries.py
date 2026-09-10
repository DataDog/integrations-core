# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import io
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from datadog_checks.base.utils import remote_queries as rq

AGENT_HOSTNAME = 'rq-proof-agent-a'


@pytest.fixture
def delivery():
    return rq.RemoteQueryResultDelivery.model_validate(
        {
            'runId': 'run-1',
            'taskId': 'task-1',
            'artifactVersion': 2,
            'uploadId': 'upload-1',
            'baseUrl': 'https://intake.example',
            'limits': {
                'maxFileBytes': 1024,
                'maxResultBytes': 8192,
                'maxRowBytes': 64,
                'maxColumns': 8,
                'maxSchemaBytes': 256,
                'maxPages': 8,
                'timeoutMs': 5000,
            },
        }
    )


@pytest.fixture
def creds(delivery):
    return rq.UploadCredentials(delivery.base_url, delivery.upload_id, 'test-api-key', 'test-app-key', None)


def receipt(page):
    return {
        'batch_index': page.batch_index,
        'record_offset': page.record_offset,
        'bytes': page.page_bytes,
        'rows': page.rows,
        'sha256': page.sha256_hex,
        'key': f'pages/{page.batch_index}.json',
    }


class Uploads:
    def __init__(self):
        self.pages = []
        self.bodies = []

    def put_page(self, creds, page, body):
        self.pages.append((page, body.read()))
        self.bodies.append(body)
        return receipt(page)

    def finalize_run(self, creds):
        return {'upload_id': creds.upload_id}


def bounded_delivery(delivery, **limits):
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(limits)
    return rq.RemoteQueryResultDelivery.model_validate(value)


@pytest.mark.parametrize('include_schema', [False, True])
def test_pages_preserve_json_rows_schema_offsets_and_receipts(delivery, creds, include_schema):
    schema = [{'column_name': 'value', 'vendor_data_type': 'text'}]
    schema_json = json.dumps(schema).encode() if include_schema else None
    row = {'value': 'a\n\u2603'}
    encoded = json.dumps(row).encode()
    prefix = rq.page_prefix(
        run_id=delivery.run_id,
        task_id=delivery.task_id,
        record_offset=0,
        agent_hostname=AGENT_HOSTNAME,
        schema_json=schema_json,
    )
    limit = len(prefix) + len(encoded) + len(rq.PAGE_SUFFIX)
    delivery = bounded_delivery(delivery, maxFileBytes=limit, maxSchemaBytes=len(schema_json or b'') or 1)
    uploads = Uploads()
    writer = rq.PageWriter(
        delivery, creds, uploads, AGENT_HOSTNAME, schema_json, lambda: None, rq.RemoteQueryRunStats()
    )
    for _ in range(3):
        writer.add_row(encoded)
    result = writer.finish()

    assert len(uploads.pages) == 3
    for index, (page, payload) in enumerate(uploads.pages):
        envelope = json.loads(payload)
        expected_keys = ['contract_version', 'crawl_id', 'task_id', 'record_offset', 'agent_hostname']
        if include_schema:
            expected_keys.append('schema')
        assert list(envelope) == expected_keys + ['data']
        assert envelope['contract_version'] == rq.REMOTE_QUERY_ARTIFACT_VERSION == 2
        assert envelope['crawl_id'] == delivery.run_id
        assert envelope['task_id'] == delivery.task_id
        assert envelope['agent_hostname'] == AGENT_HOSTNAME
        assert 'run_id' not in envelope
        assert 'batch_index' not in envelope
        assert page.batch_index == index
        assert envelope['record_offset'] == page.record_offset == index
        assert envelope['data'] == [row]
        assert page.rows == 1
        assert page.page_bytes == len(payload) <= limit
        assert page.sha256_hex == hashlib.sha256(payload).hexdigest()
        if include_schema:
            assert envelope['schema'] == schema
        else:
            assert 'schema' not in envelope
    assert result == {
        'uploadId': creds.upload_id,
        'pageCount': 3,
        'totalRows': 3,
        'totalBytes': sum(len(payload) for _, payload in uploads.pages),
    }
    assert all(body.closed for body in uploads.bodies)


@pytest.mark.parametrize('schema,pages', [(None, 0), (b'[{"column_name":"value","vendor_data_type":"int"}]', 1)])
def test_empty_result_keeps_requested_schema(delivery, creds, schema, pages):
    uploads = Uploads()
    writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, schema, lambda: None, rq.RemoteQueryRunStats())
    assert writer.finish()['pageCount'] == pages
    if pages:
        envelope = json.loads(uploads.pages[0][1])
        assert envelope['data'] == []
        assert envelope['agent_hostname'] == AGENT_HOSTNAME


@pytest.mark.parametrize(
    'bound,error', [('page', 'row_too_large'), ('count', 'max_pages_exceeded'), ('total', 'max_result_bytes_exceeded')]
)
def test_page_limits_fail_without_final_success(delivery, creds, bound, error):
    row = b'{"value":1}'
    size = (
        len(
            rq.page_prefix(
                run_id=delivery.run_id,
                task_id=delivery.task_id,
                record_offset=0,
                agent_hostname=AGENT_HOSTNAME,
                schema_json=None,
            )
        )
        + len(row)
        + len(rq.PAGE_SUFFIX)
    )
    delivery = bounded_delivery(
        delivery,
        maxFileBytes=size,
        maxSchemaBytes=1,
        maxPages=1 if bound == 'count' else 8,
        maxResultBytes=size if bound == 'total' else 8192,
    )
    uploads = Uploads()
    writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, None, lambda: None, rq.RemoteQueryRunStats())
    try:
        with pytest.raises(rq.RemoteQueryFailure) as failure:
            writer.add_row(row + b' ' if bound == 'page' else row)
            writer.add_row(row)
            writer.finish()
        assert failure.value.code == error
    finally:
        writer.discard()
    assert all(body.closed for body in uploads.bodies)


@pytest.mark.parametrize('failure', ['upload', 'receipt'])
def test_failed_upload_releases_page(delivery, creds, failure):
    bodies = []

    def put_page(_creds, page, body):
        bodies.append(body)
        if failure == 'upload':
            raise rq.RemoteQueryFailure('upload_failed', 'unavailable')
        return {**receipt(page), 'rows': page.rows + 1}

    writer = rq.PageWriter(
        delivery,
        creds,
        SimpleNamespace(put_page=put_page),
        AGENT_HOSTNAME,
        None,
        lambda: None,
        rq.RemoteQueryRunStats(),
    )
    writer.add_row(b'{"value":1}')
    with pytest.raises(rq.RemoteQueryFailure):
        writer.finish()
    assert bodies[0].closed


@pytest.mark.parametrize('trigger', ['lost_response', 'unavailable', 'in_progress'])
def test_http_page_retry_replays_exact_body_and_headers(monkeypatch, creds, trigger):
    import requests

    calls = []
    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(2, 7, len(payload), 1, hashlib.sha256(payload).hexdigest())

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data.read()))
        if len(calls) == 1:
            if trigger == 'lost_response':
                raise requests.exceptions.ConnectionError('response lost')
            status = 503 if trigger == 'unavailable' else 409
            return SimpleNamespace(status_code=status, content=b'{"error":{"code":"page_upload_in_progress"}}')
        return SimpleNamespace(status_code=200, content=json.dumps(receipt(page)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    client = rq.RequestsUploadClient()
    with io.BytesIO(payload) as body:
        assert client.put_page(creds, page, body) == receipt(page)
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('PUT', 'https://intake.example/uploads/upload-1/pages/2', payload)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/json',
        'Content-Length': str(len(payload)),
        'X-DD-Page-Bytes': str(len(payload)),
        'X-DD-Page-Rows': '1',
        'X-DD-Record-Offset': '7',
        'X-DD-Page-SHA256': page.sha256_hex,
    }


@pytest.mark.parametrize('status', [400, 403, 409])
def test_http_terminal_rejections_are_not_retried(monkeypatch, creds, status):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(status_code=status, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    page = rq.PageUploadMetadata(0, 0, 1, 1, '0' * 64)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.RequestsUploadClient().put_page(creds, page, io.BytesIO(b'x'))
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert len(calls) == 1


def test_http_page_attempt_bound_kills_slow_attempts(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []
    sent = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        sent.append(data.read())
        return SimpleNamespace(status_code=200, content=json.dumps(receipt(page)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # The wall is 100 s away, but the per-attempt bound is 55 s: the first attempt's body read
    # happens past it and is killed mid-body; the second, rewound attempt succeeds.
    clock = iter([0.0, 0.0, 56.0, 56.0, 56.0] + [56.0] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=100.0
    )
    with io.BytesIO(payload) as body:
        assert rq.RequestsUploadClient().put_page(wall_creds, page, body) == receipt(page)
    assert len(attempts) == 2
    assert sent == [payload]


def test_http_page_attempt_bound_never_exceeds_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        data.read()
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # The wall is 50 s away, inside the 55 s attempt bound, so the attempt's own deadline is
    # the wall: a partially consumed budget bounds the page attempt, the killed attempt is not
    # retried past the wall, and the run surfaces the retryable wall timeout.
    clock = iter([0.0, 0.0, 51.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq.RequestsUploadClient().put_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_retry_sequence_never_extends_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # A transient rejection followed by an expired wall: the sequence refuses to start another
    # attempt and surfaces the retryable wall timeout instead of uploading past the wall.
    clock = iter([0.0, 0.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq.RequestsUploadClient().put_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_finalize_abort_and_test_drive_routing(monkeypatch, creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')

    monkeypatch.setattr(requests, 'request', request)
    creds = rq.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, creds.app_key, 'test-intake')
    client = rq.RequestsUploadClient()
    assert client.finalize_run(creds)['upload_id'] == creds.upload_id
    client.abort(creds)
    assert [call[1] for call in calls] == [
        'https://intake.example/uploads/upload-1/finalize',
        'https://intake.example/uploads/upload-1/abort',
    ]
    assert all(
        method == 'POST' and headers['test-drive-test-intake'] == '1' and body == b'{}'
        for method, _, headers, body in calls
    )


@pytest.mark.parametrize(
    'field,bad',
    [('batch_index', 1), ('record_offset', -1), ('bytes', 2), ('rows', True), ('sha256', 'mismatch'), ('key', '')],
)
def test_receipt_must_match_produced_page(field, bad):
    page = rq.PageUploadMetadata(0, 0, 1, 1, '0' * 64)
    with pytest.raises(rq.RemoteQueryFailure, match='response'):
        rq.verify_page_response({**receipt(page), field: bad}, page)


@pytest.mark.parametrize('body', [b'', b'not-json', b'[]', b'null'])
def test_page_receipt_requires_json_object(body):
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.parse_page_receipt_body(body)
    assert failure.value.code == 'invalid_receipt'


def test_finalize_identity_must_match():
    with pytest.raises(rq.RemoteQueryFailure):
        rq.verify_run_finalize_response({'upload_id': 'other'}, 'upload-1')


@pytest.mark.parametrize(
    'target',
    [
        {},
        {'host': 'db', 'dbname': 'db'},
        {'database_instance': ' db '},
        {'database_instance': 'db', 'host': 'db'},
        {'database_instance': 'db', 'port': 5432},
        {'database_instance': 'db', 'dbname': 'other'},
        {'database_instance': 'db', 'dbname': None},
        {'database_instance': 'db', 'dbname': ''},
        {'database_instance': 'db', 'dbname': ' '},
        {'host': 'db', 'port': True, 'dbname': 'db'},
    ],
)
def test_target_requires_one_complete_selector(target):
    with pytest.raises(ValueError):
        rq.normalize_target(target)


@pytest.mark.parametrize(
    'path,value',
    [
        (('operation',), None),
        (('includeSchema',), 'true'),
        (('target', 'port'), '5432'),
        (('resultDelivery',), None),
        (('resultDelivery', 'token'), 'scoped-upload-token'),
        (('resultDelivery', 'artifactVersion'), 1),
        (('resultDelivery', 'limits', 'maxFileBytes'), 128 * 1024**2 + 1),
        (('resultDelivery', 'limits', 'maxResultBytes'), rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1),
        (('resultDelivery', 'limits', 'password'), 'SECRET_DO_NOT_LOG'),
    ],
)
def test_request_validation_rejects_malformed_instructions_without_echoing_values(delivery, path, value):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
    }
    parent = request
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryRequest.model_validate(request)
    message = rq.validation_message(failure.value)
    assert path[-1] in message
    assert 'SECRET_DO_NOT_LOG' not in message


def test_target_normalization():
    target = rq.normalize_target({'host': ' DB.EXAMPLE. ', 'port': 5432, 'dbname': 'db'})
    assert (target.host, target.port, target.dbname) == ('db.example', 5432, 'db')
    assert rq.normalize_target({'database_instance': 'Primary/DB'}).database_instance == 'Primary/DB'


@pytest.mark.parametrize(
    'mutation',
    [{'maxFileBytes': 0}, {'maxRowBytes': 2048}, {'maxSchemaBytes': 2048}, {'maxResultBytes': 512}, {'maxPages': '8'}],
)
def test_limits_reject_invalid_bounds(delivery, mutation):
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, **mutation)


def test_resolve_request_is_target_only():
    request = rq.RemoteQueryResolveRequest.model_validate(
        {'operation': 'resolve_target', 'target': {'host': 'db', 'port': 5432, 'dbname': 'db'}}
    )
    assert request.operation == 'resolve_target'
    assert (request.target.host, request.target.port, request.target.dbname) == ('db', 5432, 'db')


@pytest.mark.parametrize(
    'field,value',
    [
        ('query', 'SELECT 1'),
        ('includeSchema', True),
        ('resultDelivery', {'runId': 'run-1'}),
        ('matchFingerprint', 'deadbeef'),
        ('apiKey', 'SECRET_DO_NOT_LOG'),
    ],
)
def test_resolve_request_rejects_execution_fields_without_echoing_values(field, value):
    request = {'operation': 'resolve_target', 'target': {'database_instance': 'Primary/DB'}, field: value}

    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryResolveRequest.model_validate(request)

    assert field in rq.validation_message(failure.value)
    assert 'SECRET_DO_NOT_LOG' not in rq.validation_message(failure.value)


@pytest.mark.parametrize('operation', ['produce_json_pages', 'resolve', 'RESOLVE_TARGET', ''])
def test_resolve_request_rejects_other_operations(operation):
    request = {'operation': operation, 'target': {'database_instance': 'Primary/DB'}}

    with pytest.raises(ValidationError):
        rq.RemoteQueryResolveRequest.model_validate(request)


def test_result_ceiling_is_the_pinned_server_contract(delivery):
    # The ceiling is 100 binary GiB (stricter than decimal 100 GB): exactly that validates and
    # one byte more is rejected, so the shared ceiling cannot drift from the server-owned
    # contract or silently fall back to a smaller value.
    assert rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES == 100 * 1024**3
    limits = bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES).limits
    assert limits.max_result_bytes == rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1)


def test_page_writer_result_cap_boundaries(delivery, creds):
    # One row per page keeps the page arithmetic exact: the frame is sized to a single row, so
    # three rows produce three pages whose byte total is measured, then pinned as the exact
    # cap (the last row lands exactly on it) and one byte below it (cap-plus-one fails).
    row = b'{"value":"aaaa"}'
    frame = (
        len(
            rq.page_prefix(
                run_id=delivery.run_id,
                task_id=delivery.task_id,
                record_offset=0,
                agent_hostname=AGENT_HOSTNAME,
                schema_json=None,
            )
        )
        + len(row)
        + len(rq.PAGE_SUFFIX)
    )
    delivery = bounded_delivery(delivery, maxFileBytes=frame, maxSchemaBytes=frame, maxRowBytes=len(row), maxPages=8)

    def run(max_result_bytes):
        scoped = bounded_delivery(delivery, maxResultBytes=max_result_bytes)
        uploads = Uploads()
        writer = rq.PageWriter(scoped, creds, uploads, AGENT_HOSTNAME, None, lambda: None, rq.RemoteQueryRunStats())
        try:
            for _ in range(3):
                writer.add_row(row)
            return writer.finish(), uploads
        finally:
            writer.discard()

    measured, uploads = run(rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES)
    total = measured['totalBytes']
    assert measured['pageCount'] == 3 == len(uploads.pages)
    assert total == sum(page.page_bytes for page, _ in uploads.pages)

    # Exact cap: the third row lands exactly on maxResultBytes (the last page fits it).
    exact, exact_uploads = run(total)
    assert exact['totalBytes'] == total
    assert [page.batch_index for page, _ in exact_uploads.pages] == [0, 1, 2]

    # Cap-plus-one: one byte less budget fails the row that would cross the cap.
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        run(total - 1)
    assert failure.value.code == 'max_result_bytes_exceeded'
    assert all(body.closed for body in exact_uploads.bodies)


@pytest.mark.parametrize('value,expected', [(None, True), (' yes ', True), ('false', False), (False, False)])
def test_allowlist_default_and_config(monkeypatch, value, expected):
    monkeypatch.setattr(rq.datadog_agent, 'get_config', lambda _: value)
    assert rq.is_query_allowlist_enabled() is expected


@pytest.mark.parametrize(
    'value,expected',
    [
        (' TEST-INTAKE ', 'test-intake'),
        (None, None),
        ('', None),
        ('-intake', None),
        ('a' * 64, None),
        ('x\r\nAuthorization: y', None),
    ],
)
def test_test_drive_name_cannot_inject_headers(value, expected):
    assert rq.validate_test_drive_name(value) == expected
