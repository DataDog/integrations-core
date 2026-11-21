# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import descriptor, source_page


class SpecIntake:
    """HTTP double for the spec intake's strict requests and empty success responses."""

    def __init__(self):
        self.requests = []
        self.registered = False
        self.page_count = 0
        intake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.respond()

            def do_PUT(self) -> None:
                self.respond()

            def log_message(self, *args: Any) -> None:
                pass

            def respond(self) -> None:
                length = int(self.headers.get('Content-Length', '-1'))
                body = self.rfile.read(length) if length >= 0 else b''
                intake.requests.append((self.command, self.path, dict(self.headers), body))
                code = None
                if self.path.endswith('/descriptor'):
                    value = json.loads(body)
                    if set(value) != {'format_version', 'include_schema', 'agent_hostname', 'columns'} or any(
                        set(column) != {'column_name', 'vendor_data_type', 'logical_type'}
                        for column in value['columns']
                    ):
                        code = 'invalid_argument'
                    else:
                        intake.registered = True
                elif '/pages/' in self.path:
                    if not intake.registered:
                        code = 'failed_precondition'
                    elif length < 0 or self.headers.get('Content-Encoding', 'identity') != 'identity':
                        code = 'invalid_argument'
                    elif (
                        self.headers.get('X-DD-Source-Page-Rows') is None
                        or self.headers.get('X-DD-Record-Offset') is None
                    ):
                        code = 'invalid_argument'
                    else:
                        intake.page_count += 1
                elif self.path.endswith('/finalize'):
                    value = json.loads(body)
                    if set(value) != {'expected_page_count'}:
                        code = 'invalid_argument'
                    elif value['expected_page_count'] != intake.page_count or not intake.page_count:
                        code = 'failed_precondition'
                if code:
                    payload = json.dumps({'error': {'code': code, 'message': 'request rejected'}}).encode()
                    self.send_response(400 if code == 'invalid_argument' else 409)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                else:
                    self.send_response(204)
                    self.end_headers()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.base_url = 'http://127.0.0.1:{}'.format(self.server.server_address[1])

    def __enter__(self) -> 'SpecIntake':
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def test_upload_client_completes_the_spec_intake_protocol():
    # Real HTTP verifies fixed-length page framing and prevents a successful, empty 204
    # from being mistaken for a missing JSON receipt at any step of the run.
    client = rq_upload.RequestsUploadClient()
    body = rq_contract.descriptor_request_bytes(descriptor())
    payload = b'"""hello"""\n'
    with SpecIntake() as intake:
        creds = rq_upload.UploadCredentials(intake.base_url, 'upload-1', 'test-api-key', None)
        client.register_descriptor(creds, body)
        with io.BytesIO(payload) as page_body:
            client.put_source_page(creds, source_page(payload, record_offset=0), page_body)
        client.finalize_run(creds, 1)
        # Abort a different, still-open session: finalized sessions cannot be aborted.
        client.abort(rq_upload.UploadCredentials(intake.base_url, 'upload-2', 'test-api-key', None))

    assert [path.rsplit('/', 1)[-1] for _, path, _, _ in intake.requests] == ['descriptor', '0', 'finalize', 'abort']
    columns = json.loads(intake.requests[0][3])['columns']
    assert all(set(column) == {'column_name', 'vendor_data_type', 'logical_type'} for column in columns)
    _, _, headers, uploaded = intake.requests[1]
    assert uploaded == payload
    assert headers['Content-Length'] == str(len(payload))
    assert headers['X-DD-Source-Page-Rows'] == '1'
    assert headers['X-DD-Record-Offset'] == '0'
    assert headers['Content-Type'] == 'text/csv'
    assert 'Transfer-Encoding' not in headers
    assert 'Content-Encoding' not in headers
    assert 'X-DD-Source-Page-Bytes' not in headers
    assert all(headers['dd-api-key'] == 'test-api-key' for _, _, headers, _ in intake.requests)


@pytest.mark.parametrize('unknown_field', ['extra', 'array_element_delimiter'])
def test_strict_intake_rejection_reports_its_code_without_retrying(unknown_field: str):
    # A descriptor that drifts from the strict intake shape must fail immediately with
    # its public code, rather than silently discarding metadata or retrying forever.
    body = json.loads(rq_contract.descriptor_request_bytes(descriptor()))
    body['columns'][0][unknown_field] = None
    with SpecIntake() as intake:
        creds = rq_upload.UploadCredentials(intake.base_url, 'upload-1', 'test-api-key', None)
        with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
            rq_upload.RequestsUploadClient().register_descriptor(creds, json.dumps(body).encode())
    assert failure.value.code == 'upload_failed'
    assert 'invalid_argument' in failure.value.message
    assert len(intake.requests) == 1
