# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from google.protobuf.json_format import MessageToJson

from .sds_result_payload_pb2 import ScannerMetadata, ScanStats, SdsResultPayload

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

# Must match the event type registered by the Agent's event-platform forwarder
# (comp/forwarder/eventplatform/def/component.go -> EventTypeSDSResult). The forwarder
# routes this track to the sds-intake (/api/v2/sdsresult) and serializes the body as
# protobuf (application/x-protobuf, gzip), one payload per request.
EVENT_TRACK_TYPE = 'sds-result'


def _build_scan_match(match: Mapping[str, Any]) -> SdsResultPayload.ScanMatch:
    pb = SdsResultPayload.ScanMatch(
        rule_id=match.get('rule_id', ''),
        start_index=int(match.get('start_index', 0)),
        end_index=int(match.get('end_index', 0)),
        sample=match.get('sample', ''),
    )
    # Optional scalar fields are only set when present so the wire stays minimal.
    for field in (
        'path',
        'line',
        'column',
        'start_line',
        'end_line',
        'row',
        'start_index_in_line',
        'end_index_in_line',
        'match_status',
    ):
        if match.get(field) is not None:
            setattr(pb, field, match[field])
    return pb


def _build_db_match(db_match: Mapping[str, Any]) -> SdsResultPayload.DbMatch:
    return SdsResultPayload.DbMatch(
        rule_id=db_match.get('rule_id', ''),
        column_name=db_match.get('column_name', ''),
        count_matched_rows=int(db_match.get('count_matched_rows', 0)),
        count_total_rows=int(db_match.get('count_total_rows', 0)),
    )


def _build_scan_result(result: Mapping[str, Any]) -> SdsResultPayload.ScanResult:
    pb = SdsResultPayload.ScanResult(duration=int(result.get('duration', 0)))
    pb.matches.extend(_build_scan_match(m) for m in result.get('matches', ()))
    pb.db_matches.extend(_build_db_match(m) for m in result.get('db_matches', ()))

    location = result.get('location')
    if location:
        loc = pb.location
        rds_table = location.get('rds_table')
        if rds_table:
            # RDS resources are routed to the backend RdsExtractor, which reads matches and the
            # location exclusively from the `rdsTable` oneof (the flat fields below are ignored).
            rt = loc.rdsTable
            if rds_table.get('instance_arn') is not None:
                rt.instance_arn = rds_table['instance_arn']
            if rds_table.get('snapshot_arn') is not None:
                rt.snapshot_arn = rds_table['snapshot_arn']
            if rds_table.get('snapshot_timestamp') is not None:
                rt.snapshot_timestamp = int(rds_table['snapshot_timestamp'])
            if rds_table.get('database_name') is not None:
                rt.database_name = rds_table['database_name']
            if rds_table.get('table_name') is not None:
                rt.table_name = rds_table['table_name']
        # Deprecated flat fields are still populated for backward compatibility with the intake
        # (used by the file/S3 path; ignored for RDS).
        if location.get('database') is not None:
            loc.database = location['database']
        if location.get('table') is not None:
            loc.table = location['table']
        if location.get('size_in_bytes') is not None:
            loc.size_in_bytes = int(location['size_in_bytes'])
        if location.get('last_modified_timestamp') is not None:
            loc.last_modified_timestamp = int(location['last_modified_timestamp'])
    return pb


def build_payload(
    *,
    resource_type: str,
    resource_name: str,
    scan_results: Iterable[Mapping[str, Any]],
    timestamp_ms: int | None = None,
    region: str | None = None,
    scanner_version: str | None = None,
    stats: Mapping[str, Any] | None = None,
    rules: Mapping[str, Mapping[str, Any]] | None = None,
    scan_source: int = SdsResultPayload.AGENTLESS,
) -> SdsResultPayload:
    """Build an ``SdsResultPayload`` protobuf message from structured findings.

    The schema is shared with the agentless scanner (see ``sds_result_payload.proto``); this
    keeps the Agent-emitted payload wire-compatible with the sds-intake.

    ``scan_source`` defaults to ``AGENTLESS`` because the intake worker drops any event with an
    ``UNKNOWN`` source. Until a dedicated ``AGENT`` value is added to the shared proto (and
    accepted by the backend), Agent-emitted results impersonate the agentless source.
    """
    payload = SdsResultPayload(
        scan_source=scan_source,
        timestamp=timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
    )
    payload.resource.type = resource_type
    payload.resource.name = resource_name
    payload.scan_results.extend(_build_scan_result(r) for r in scan_results)

    if stats:
        payload.scan_stats.CopyFrom(
            ScanStats(
                scan_duration_ms=int(stats.get('scan_duration_ms', 0)),
                total_files_found=int(stats.get('total_files_found', 0)),
                files_scanned=int(stats.get('files_scanned', 0)),
                total_data_scanned_bytes=int(stats.get('total_data_scanned_bytes', 0)),
            )
        )

    if region is not None or scanner_version is not None:
        meta = ScannerMetadata()
        if scanner_version is not None:
            meta.version = scanner_version
        if region is not None:
            meta.region = region
        payload.scanner_metadata.CopyFrom(meta)

    if rules:
        for rule_id, info in rules.items():
            rule_pb = payload.rules[rule_id]
            rule_pb.id = info.get('id', rule_id)
            rule_pb.name = info.get('name', '')
            rule_pb.priority = info.get('priority', '')
            rule_pb.tags.extend(info.get('tags', ()))
            rule_pb.labels.extend(info.get('labels', ()))

    return payload


def emit_sds_results(check: PostgreSql, payload: SdsResultPayload) -> None:
    """Serialize ``payload`` to protobuf bytes and send it to the sds-intake.

    Uses the binary-safe ``event_platform_event_raw`` so the protobuf bytes reach the intake
    intact (the regular ``event_platform_event`` would corrupt them via UTF-8 coercion).
    """
    raw_event = payload.SerializeToString()
    # Log the JSON-marshalled payload so it is visible what is actually being sent on the wire
    # (the protobuf bytes themselves are not human-readable).
    check.log.info(
        "sds-result: emitting %d-byte protobuf payload to track '%s':\n%s",
        len(raw_event),
        EVENT_TRACK_TYPE,
        MessageToJson(payload, preserving_proto_field_name=True),
    )
    check.event_platform_event_raw(raw_event, EVENT_TRACK_TYPE)
