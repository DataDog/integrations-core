# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import hashlib
import json

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing

AGENT_HOSTNAME = 'rq-proof-agent-a'


TRACE_ID = '1234567890123456789'


PARENT_ID = '9876543210987654321'


def descriptor(
    columns=(('value', 'text', 'string'),),
    include_schema=False,
    agent_hostname=AGENT_HOSTNAME,
    format_version=None,
):
    """Build a descriptor; a column may carry its array element delimiter as a 4th element."""
    column_kwargs = []
    for column in columns:
        name, vendor, logical = column[:3]
        delimiter = column[3] if len(column) > 3 else None
        if delimiter is None:
            column_kwargs.append({'column_name': name, 'vendor_data_type': vendor, 'logical_type': logical})
        else:
            column_kwargs.append(
                {
                    'column_name': name,
                    'vendor_data_type': vendor,
                    'logical_type': logical,
                    'array_element_delimiter': delimiter,
                }
            )
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
    """A fake intake: registers the descriptor, accepts source pages, and finalizes the run.

    Page PUTs answer the pinned acceptance receipt — no per-page final metadata exists at
    acceptance — and finalize returns authoritative totals over the recorded pages, so run
    stats and the compact receipt come from finalization, never from local sizes.
    """

    def __init__(
        self,
        final_growth=0,
        put_failure=None,
        receipt_bytes=None,
        receipt_override=None,
        descriptor_response=None,
        finalize_response=None,
    ):
        self.final_growth = final_growth
        self.put_failure = put_failure
        self.receipt_bytes = receipt_bytes
        self.receipt_override = receipt_override
        self.descriptor_response = descriptor_response
        self.finalize_response = finalize_response
        self.descriptor_bodies = []
        self.put_attempts = []
        self.pages = []
        self.finalize_calls = 0
        self.finalize_expected_counts = []
        self.abort_calls = 0

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        if self.descriptor_response is not None:
            return self.descriptor_response
        # Intake's pinned receipt: the registered descriptor's identity plus the sha256 over
        # the canonical registration bytes.
        registered = json.loads(body)
        return {
            'upload_id': creds.upload_id,
            'format_version': registered['format_version'],
            'include_schema': registered['include_schema'],
            'columns': len(registered['columns']),
            'sha256': hashlib.sha256(body).hexdigest(),
        }

    def final_bytes_for(self, page):
        if self.receipt_bytes is not None:
            return self.receipt_bytes(page) + self.final_growth
        return page.source_bytes + self.final_growth

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_attempts.append((page, payload))
        if self.put_failure is not None:
            failure = self.put_failure(page)
            if failure is not None:
                raise failure
        self.pages.append((page, payload))
        if self.receipt_override is not None:
            return self.receipt_override(page)
        return {
            'upload_id': creds.upload_id,
            'batch_index': page.batch_index,
            'record_offset': page.record_offset,
            'source_rows': page.rows,
            'status': 'accepted',
        }

    def finalize_run(self, creds, expected_page_count):
        self.finalize_calls += 1
        self.finalize_expected_counts.append(expected_page_count)
        if self.finalize_response is not None:
            return self.finalize_response
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.pages),
            'total_rows': sum(page.rows for page, _ in self.pages),
            'total_bytes': sum(self.final_bytes_for(page) for page, _ in self.pages),
        }

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


def descriptor_receipt(body, **overrides):
    """Intake's pinned descriptor receipt for one registration body, with field overrides."""
    registered = json.loads(body)
    receipt = {
        'upload_id': 'upload-1',
        'format_version': registered['format_version'],
        'include_schema': registered['include_schema'],
        'columns': len(registered['columns']),
        'sha256': hashlib.sha256(body).hexdigest(),
    }
    receipt.update(overrides)
    return receipt


def source_page(payload, batch_index=0, record_offset=7):
    return rq_contract.SourcePageUploadMetadata(
        batch_index=batch_index,
        record_offset=record_offset,
        source_bytes=len(payload),
        rows=1,
    )


def acceptance_receipt(batch_index, record_offset, source_rows, upload_id='upload-1', status='accepted'):
    """The pinned page acceptance receipt for one accepted source page."""
    return {
        'upload_id': upload_id,
        'batch_index': batch_index,
        'record_offset': record_offset,
        'source_rows': source_rows,
        'status': status,
    }


def pending_receipt(completed_page_count, expected_page_count, status='processing'):
    """The pinned 202 finalize pending receipt for one still-processing run."""
    return {
        'status': status,
        'completed_page_count': completed_page_count,
        'expected_page_count': expected_page_count,
    }


def finalize_receipt(page_count=1, total_rows=0, total_bytes=0, upload_id='upload-1'):
    """The pinned authoritative final receipt intake answers on HTTP 200."""
    return {
        'upload_id': upload_id,
        'page_count': page_count,
        'total_rows': total_rows,
        'total_bytes': total_bytes,
    }


def receipt(page):
    return acceptance_receipt(page.batch_index, page.record_offset, page.rows)


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
