# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest
from pydantic import ValidationError

from datadog_checks.base.utils.remote_queries import contract as rq_contract

from .helpers import AGENT_HOSTNAME, PARENT_ID, TRACE_ID, bounded_delivery, descriptor


def test_descriptor_request_bytes_are_canonical_and_deterministic():
    def build():
        return descriptor(
            columns=(('value', 'text', 'string'), ('payload', 'bytea', 'binary')),
            include_schema=True,
        )

    expected = (
        b'{"format_version":"csv-json-cell-v1","include_schema":true,'
        b'"agent_hostname":"rq-proof-agent-a","columns":['
        b'{"column_name":"value","vendor_data_type":"text","logical_type":"string",'
        b'"array_element_delimiter":null},'
        b'{"column_name":"payload","vendor_data_type":"bytea","logical_type":"binary",'
        b'"array_element_delimiter":null}]}'
    )
    assert rq_contract.descriptor_request_bytes(build()) == expected
    # A fresh construction produces a byte-identical registration body for retries.
    assert rq_contract.descriptor_request_bytes(build()) == expected


@pytest.mark.parametrize(
    'columns,include_schema,agent_hostname',
    [
        ((), True, AGENT_HOSTNAME),  # no columns
        ((('value', 'text', 'string'), ('value', 'int4', 'integer')), False, AGENT_HOSTNAME),  # duplicate names
        ((('value', 'text', 'unknown_family'),), False, AGENT_HOSTNAME),  # closed logical-type set
        ((('value', 'text', 'string'),), False, ''),  # empty hostname
        ((('', 'text', 'string'),), False, AGENT_HOSTNAME),  # empty column name
        ((('value', '', 'string'),), False, AGENT_HOSTNAME),  # empty vendor type
    ],
)
def test_descriptor_rejects_malformed_columns(columns, include_schema, agent_hostname):
    with pytest.raises(ValidationError):
        descriptor(columns=columns, include_schema=include_schema, agent_hostname=agent_hostname)


def test_descriptor_request_and_schema_bytes_emit_valid_non_ascii_as_raw_utf8():
    """Intake's canonical encoder emits valid non-ASCII as raw UTF-8, never ``\\uXXXX`` escapes.

    The registration body and the schema bytes it derives from the descriptor must spell
    non-ASCII identically, because intake checksums exactly these canonical bytes.
    """

    def build():
        return descriptor(
            columns=(('colonné', 'véndor', 'string'),),
            include_schema=True,
            agent_hostname='agent-hôte',
        )

    body = rq_contract.descriptor_request_bytes(build())
    assert body == (
        b'{"format_version":"csv-json-cell-v1","include_schema":true,'
        b'"agent_hostname":"agent-h\xc3\xb4te","columns":'
        b'[{"column_name":"colonn\xc3\xa9","vendor_data_type":"v\xc3\xa9ndor","logical_type":"string",'
        b'"array_element_delimiter":null}]}'
    )
    assert b'\\u' not in body
    assert rq_contract.descriptor_request_bytes(build()) == body
    assert rq_contract.descriptor_schema_bytes(build()) == (
        b'[{"column_name":"colonn\xc3\xa9","vendor_data_type":"v\xc3\xa9ndor"}]'
    )


@pytest.mark.parametrize(
    'columns,agent_hostname,valid',
    [
        # 255 UTF-8 bytes of a two-byte character (128 characters) pass the name limits.
        ((('a' + 'é' * 127, 'text', 'string'),), AGENT_HOSTNAME, True),
        # 256 bytes is over the byte limit even though 128 characters passes a character count.
        ((('é' * 128, 'text', 'string'),), AGENT_HOSTNAME, False),
        # The vendor-type limit is 1024 bytes.
        ((('value', 'é' * 512, 'string'),), AGENT_HOSTNAME, True),
        ((('value', 'a' + 'é' * 512, 'string'),), AGENT_HOSTNAME, False),
        ((('value', 'text', 'string'),), 'a' + 'é' * 127, True),
        ((('value', 'text', 'string'),), 'é' * 128, False),
    ],
)
def test_descriptor_limits_bound_utf8_bytes_not_character_counts(columns, agent_hostname, valid):
    """The server limits are byte limits: multibyte text within the character count but over
    the byte count is rejected, and text at exactly the byte boundary passes.
    """
    if valid:
        descriptor(columns=columns, agent_hostname=agent_hostname)
    else:
        with pytest.raises(ValidationError):
            descriptor(columns=columns, agent_hostname=agent_hostname)


@pytest.mark.parametrize(
    'columns,agent_hostname',
    [
        ((('a\ud800', 'text', 'string'),), AGENT_HOSTNAME),
        ((('value', 'a\ud800', 'string'),), AGENT_HOSTNAME),
        ((('value', 'text', 'string'),), 'a\ud800'),
    ],
)
def test_descriptor_text_that_cannot_encode_as_utf8_fails_validation(columns, agent_hostname):
    """A lone surrogate cannot ride the UTF-8 wire, so it is rejected at validation instead
    of crashing the canonical JSON encoding mid-upload."""
    with pytest.raises(ValidationError):
        descriptor(columns=columns, agent_hostname=agent_hostname)


def test_request_trace_context_parses_the_agent_carrier(delivery):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
    }
    # Absence is valid for mixed versions: an Agent that never sends the field — and an
    # explicit null — carries no context and the request parses exactly as before.
    assert rq_contract.RemoteQueryRequest.model_validate(request).trace_context is None
    assert rq_contract.RemoteQueryRequest.model_validate({**request, 'traceContext': None}).trace_context is None

    context = rq_contract.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}}
    ).trace_context
    assert (context.trace_id, context.parent_id, context.sampling_priority) == (TRACE_ID, PARENT_ID, 2)

    # The full uint64 range and both positive keep priorities are accepted; a zero-padded
    # spelling of the same value validates to the canonical decimal spelling, so the
    # injected header values are byte-stable.
    context = rq_contract.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': '18446744073709551615', 'parentId': PARENT_ID, 'samplingPriority': 1}}
    ).trace_context
    assert (context.trace_id, context.sampling_priority) == ('18446744073709551615', 1)
    context = rq_contract.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': '00' + TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}}
    ).trace_context
    assert context.trace_id == TRACE_ID


@pytest.mark.parametrize(
    'mutation',
    [
        {'traceId': '0'},
        {'traceId': '00'},
        {'traceId': '18446744073709551616'},
        {'traceId': '-42'},
        {'traceId': '0x2a'},
        {'traceId': '42 '},
        {'traceId': '1.5'},
        {'traceId': ''},
        {'traceId': 12345678901234567890},
        {'parentId': '0'},
        {'parentId': '1e3'},
        {'samplingPriority': 0},
        {'samplingPriority': -1},
        {'samplingPriority': 3},
        {'samplingPriority': '2'},
        {'samplingPriority': 2.0},
        {'samplingPriority': True},
    ],
)
def test_request_trace_context_is_strict_without_echoing_values(delivery, mutation):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
        'traceContext': {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2},
    }
    request['traceContext'].update(mutation)

    with pytest.raises(ValidationError) as failure:
        rq_contract.RemoteQueryRequest.model_validate(request)

    message = rq_contract.validation_message(failure.value)
    assert 'traceContext' in message
    # The carrier is observability metadata; a validation error never echoes its values.
    assert TRACE_ID not in message
    assert PARENT_ID not in message


@pytest.mark.parametrize(
    'carrier',
    [
        {},
        {'traceId': TRACE_ID},
        {'traceId': TRACE_ID, 'parentId': PARENT_ID},
        {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2, 'origin': 'extra'},
        'not-an-object',
        5,
    ],
)
def test_request_trace_context_is_a_closed_shape(delivery, carrier):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
        'traceContext': carrier,
    }

    with pytest.raises(ValidationError) as failure:
        rq_contract.RemoteQueryRequest.model_validate(request)

    assert 'traceContext' in rq_contract.validation_message(failure.value)


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
        rq_contract.RemoteQueryTarget.model_validate(target)


@pytest.mark.parametrize(
    'path,value',
    [
        (('extra',), 'SECRET_DO_NOT_LOG'),
        (('password',), 'SECRET_DO_NOT_LOG'),
        (('operation',), None),
        (('includeSchema',), 'true'),
        (('target', 'port'), '5432'),
        (('resultDelivery',), None),
        (('resultDelivery', 'token'), 'scoped-upload-token'),
        (('resultDelivery', 'artifactVersion'), 2),
        (('resultDelivery', 'limits', 'maxFileBytes'), 128 * 1024**2 + 1),
        (('resultDelivery', 'limits', 'maxResultBytes'), rq_contract.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1),
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
        rq_contract.RemoteQueryRequest.model_validate(request)
    message = rq_contract.validation_message(failure.value)
    assert path[-1] in message
    assert 'SECRET_DO_NOT_LOG' not in message


def test_target_normalization():
    target = rq_contract.RemoteQueryTarget.model_validate({'host': ' DB.EXAMPLE. ', 'port': 5432, 'dbname': 'db'})
    assert (target.host, target.port, target.dbname) == ('db.example', 5432, 'db')
    assert (
        rq_contract.RemoteQueryTarget.model_validate({'database_instance': 'Primary/DB'}).database_instance
        == 'Primary/DB'
    )


@pytest.mark.parametrize(
    'mutation',
    [{'maxFileBytes': 0}, {'maxRowBytes': 2048}, {'maxSchemaBytes': 2048}, {'maxResultBytes': 512}, {'maxPages': '8'}],
)
def test_limits_reject_invalid_bounds(delivery, mutation):
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, **mutation)


def test_resolve_request_is_target_only():
    request = rq_contract.RemoteQueryResolveRequest.model_validate(
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
        ('traceContext', {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}),
        ('matchFingerprint', 'deadbeef'),
        ('apiKey', 'SECRET_DO_NOT_LOG'),
    ],
)
def test_resolve_request_rejects_execution_fields_without_echoing_values(field, value):
    request = {'operation': 'resolve_target', 'target': {'database_instance': 'Primary/DB'}, field: value}

    with pytest.raises(ValidationError) as failure:
        rq_contract.RemoteQueryResolveRequest.model_validate(request)

    assert field in rq_contract.validation_message(failure.value)
    assert 'SECRET_DO_NOT_LOG' not in rq_contract.validation_message(failure.value)


@pytest.mark.parametrize('operation', ['produce_json_pages', 'resolve', 'RESOLVE_TARGET', ''])
def test_resolve_request_rejects_other_operations(operation):
    request = {'operation': operation, 'target': {'database_instance': 'Primary/DB'}}

    with pytest.raises(ValidationError):
        rq_contract.RemoteQueryResolveRequest.model_validate(request)


def test_result_ceiling_is_the_pinned_server_contract(delivery):
    # The ceiling is 100 binary GiB (stricter than decimal 100 GB): exactly that validates and
    # one byte more is rejected, so the shared ceiling cannot drift from the server-owned
    # contract or silently fall back to a smaller value.
    assert rq_contract.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES == 100 * 1024**3
    limits = bounded_delivery(delivery, maxResultBytes=rq_contract.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES).limits
    assert limits.max_result_bytes == rq_contract.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, maxResultBytes=rq_contract.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1)
