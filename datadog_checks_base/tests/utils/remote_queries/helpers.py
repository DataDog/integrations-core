# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing

AGENT_HOSTNAME = 'rq-proof-agent-a'


TRACE_ID = '1234567890123456789'


PARENT_ID = '9876543210987654321'


def as_session_request(request):
    """Adapt a fake `request(method, url, headers, data, timeout)` to patch `requests.Session.request`.

    The upload client sends each attempt through its own session, so tests intercept the
    session's request method rather than `requests.request`.
    """

    def session_request(session, *args, **kwargs):
        assert kwargs.pop('allow_redirects') is False
        return request(*args, **kwargs)

    return session_request


def descriptor(
    columns=(('value', 'text', 'string'),),
    include_schema=False,
    agent_hostname=AGENT_HOSTNAME,
    format_version=None,
):
    """Build a source descriptor with exactly the supported column fields."""
    column_kwargs = [
        {'column_name': name, 'vendor_data_type': vendor, 'logical_type': logical} for name, vendor, logical in columns
    ]
    return rq_contract.RemoteQueryUploadDescriptor(
        format_version=format_version
        if format_version is not None
        else rq_contract.REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION,
        include_schema=include_schema,
        agent_hostname=agent_hostname,
        columns=[rq_contract.RemoteQueryDescriptorColumn(**kwargs) for kwargs in column_kwargs],
    )


def string_cell(text):
    """One encoded string cell: its canonical JSON token and the redactable-leaf final bound."""
    token = json.dumps(text, ensure_ascii=False).encode('utf-8')
    return rq_pages.EncodedCell(token, rq_pages.redactable_leaf_final_bound(token))


def cell(token, final_bound):
    return rq_pages.EncodedCell(token, final_bound)


def csv_field(token):
    """The expected CSV field for one token, computed independently of the producer's framing."""
    if b'"' in token or b',' in token or b'\n' in token:
        return b'"' + token.replace(b'"', b'""') + b'"'
    return token


def csv_record(tokens):
    return b','.join(csv_field(token) for token in tokens) + b'\n'


def envelope_bound(delivery, record_offset, schema_json=None):
    """The final-JSON envelope bound for one page: intake's envelope plus the closing bytes."""
    return len(
        rq_pages.page_prefix(
            run_id=delivery.run_id,
            task_id=delivery.task_id,
            record_offset=record_offset,
            agent_hostname=AGENT_HOSTNAME,
            schema_json=schema_json,
        )
    ) + len(rq_pages.PAGE_SUFFIX)


class Uploads:
    """A synchronous intake double: successes return no data."""

    def __init__(self, put_failure=None, descriptor_failure=None):
        self.put_failure = put_failure
        self.descriptor_failure = descriptor_failure
        self.descriptor_bodies = []
        self.put_attempts = []
        self.pages = []
        self.finalize_calls = 0
        self.finalize_expected_counts = []
        self.abort_calls = 0

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        if self.descriptor_failure is not None:
            raise self.descriptor_failure

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_attempts.append((page, payload))
        if self.put_failure is not None:
            failure = self.put_failure(page)
            if failure is not None:
                raise failure
        self.pages.append((page, payload))

    def finalize_run(self, creds, expected_page_count):
        self.finalize_calls += 1
        self.finalize_expected_counts.append(expected_page_count)

    def abort(self, creds):
        self.abort_calls += 1


def bounded_delivery(delivery, **limits):
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(limits)
    return rq_contract.RemoteQueryResultDelivery.model_validate(value)


def make_writer(delivery, creds, uploads, source_descriptor=None, include_schema=False):
    return rq_pages.SourcePageWriter(
        delivery,
        creds,
        uploads,
        source_descriptor if source_descriptor is not None else descriptor(include_schema=include_schema),
        lambda: None,
        rq_contract.RemoteQueryRunStats(),
    )


def source_page(payload, batch_index=0, record_offset=7):
    return rq_contract.SourcePageUploadMetadata(
        batch_index=batch_index,
        record_offset=record_offset,
        source_bytes=len(payload),
        rows=1,
    )


# ---------------------------------------------------------------------------
# Native producer tracing doubles
# ---------------------------------------------------------------------------


class FakeSpan:
    """A recording span double: tags, metrics, and finish — no ddtrace, no writer."""

    def __init__(self, name, child_of, service=None, resource=None, activate=None):
        self.name = name
        self.child_of = child_of
        self.service = service
        self.resource = resource
        self.activate = activate
        self.span_id = None
        self.tags = {}
        self.metrics = {}
        self.error = 0
        self.finished = False

    def set_tag(self, key, value):
        self.tags[key] = value

    def set_metric(self, key, value):
        self.metrics[key] = value

    def finish(self):
        self.finished = True


class FakeTracer:
    """A recording tracer double: starts spans and counts flushes, never sends."""

    def __init__(self, refuse_span=None, refuse_flush=False):
        self.spans = []
        self.flushes = 0
        self.refuse_span = refuse_span
        self.refuse_flush = refuse_flush

    def start_span(
        self, name, child_of=None, service=None, resource=None, span_type=None, activate=False, span_api='datadog'
    ):
        if self.refuse_span == name:
            raise RuntimeError('span start refused')
        span = FakeSpan(name, child_of, service=service, resource=resource, activate=activate)
        span.span_id = len(self.spans) + 1
        self.spans.append(span)
        return span

    def flush(self):
        self.flushes += 1
        if self.refuse_flush:
            raise RuntimeError('flush refused')

    def by_name(self, name):
        return [span for span in self.spans if span.name == name]


class FakePropagator:
    """A recording propagator double: injects the span's own id as the trace parent.

    The real ``HTTPPropagator`` answers the same observable contract for a span: the
    injected parent id is the span's own id, so a request carrying the injected headers
    becomes that span's child — never a sibling of the run's action parent.
    """

    def __init__(self):
        self.injected = []

    def inject(self, span, headers):
        self.injected.append((span, dict(headers)))
        headers[rq_contract.REMOTE_QUERY_TRACE_ID_HEADER] = '222'
        headers[rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] = str(span.span_id)
        headers[rq_contract.REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER] = '1'


class RefusingPropagator(FakePropagator):
    """A propagator double whose injection fails, exercising the manual-header fallback."""

    def inject(self, span, headers):
        raise RuntimeError('inject refused')


class FakeParentContext:
    """A stand-in for the ddtrace Context the factory builds from the request carrier."""

    def __init__(self, trace_id, span_id, sampling_priority):
        self.trace_id = trace_id
        self.span_id = span_id
        self.sampling_priority = sampling_priority


def make_tracing(integration='postgres', propagator=None, **tracer_kwargs):
    """A producer tracing over the fake doubles, parented on a sentinel request carrier."""
    tracer = FakeTracer(**tracer_kwargs)
    parent = FakeParentContext(int(TRACE_ID), int(PARENT_ID), 2)
    return (
        rq_tracing.RemoteQueryProducerTracing(
            tracer, propagator if propagator is not None else FakePropagator(), parent, integration
        ),
        tracer,
    )
