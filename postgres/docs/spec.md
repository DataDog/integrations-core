# Postgres integration remote queries: specification

## Purpose

The Postgres Agent integration runs Remote Queries for its loaded checks. When the Agent asks, a check says whether it serves the requested database. When the Agent hands it a query, the check runs the query in a read-only transaction on that database, and uploads the database's own COPY CSV output, split into pages, to `its-agent-intake`, which converts the pages into JSON result files. The check then finalizes the upload and answers the Agent with success or an error.

The integration does not choose which Agent or check runs a query (the [Agent](https://dd-quick.us1.staging.dog/datadog-agent-spec/) and the `its-agent` worker do), validate SQL (ITS does), write result files or scan for sensitive data (intake does), or report run status to ITS (the worker does). Its only caller is the core Agent.

## Terms

- **Agent:** the core Datadog Agent, which calls the integration (Agent spec, Terms).
- **Check:** one loaded Postgres check, built from one instance configuration.
- **Target, delivery instructions, run:** as defined in the [Agent spec](https://dd-quick.us1.staging.dog/datadog-agent-spec/).
- **Intake:** `its-agent-intake`, which receives pages and stores the result files.
- **Upload session, descriptor, page, result file, page index, record offset:** as defined in the [intake spec](https://dd-quick.us1.staging.dog/its-agent-intake-spec/).
- **Record:** one result row as the database's COPY output writes it: its fields and the line break that ends it.
- **Column type:** a result column's type, with domains resolved to their base type.
- **Monitoring scope:** the databases a check monitors: its configured database and, when database autodiscovery is on, the databases its autodiscovery currently admits.
- **Result file size target:** the result file size in the delivery instructions. The integration aims for it when it builds pages (SIZE-01), on a best-effort basis; intake, not the integration, enforces any hard cap.
- **Row size limit, page count limit, total result size limit, column limit, schema size limit:** the limits in the delivery instructions, which intake returned when it created the session.
- **Run time limit:** the query time limit in the delivery instructions (its-agent TIME-03).

## Receiving a request

### REQ-01 — Serve two operations

The integration serves two operations: resolve and execute (annex). A request for any other operation, or one that is not a JSON object, fails as an invalid request.

### REQ-02 — Validate a request before using it

A match check carries only the operation and the target. A query request carries the operation, the target, a non-empty query, the schema choice, the delivery instructions, and optionally the trace context. The target and the delivery instructions follow the Agent's rules (Agent INPUT-03, INPUT-04). A request with an unknown field or a missing or invalid value fails as an invalid request, without contacting the database or intake.

### REQ-03 — Require the Agent's API key

When the Agent has no API key configured, a query request fails before connecting to the database.

## Matching the target

### MATCH-01 — Match a host, port, and database target

A check serves a host, port, and database target when all of these hold:

- its configured host equals the target's host, both trimmed of surrounding spaces, lowercased, and without one trailing dot;
- its port equals the target's port;
- the target's database is in its monitoring scope, compared exactly.

A check whose configuration has no usable host or port serves no such target.

### MATCH-02 — Match a database instance target

A check serves a database instance target when its database identifier, which the check renders from its configuration for its own telemetry, equals the target's name exactly. The run uses the check's configured database.

### MATCH-03 — Match from what the check already knows

Matching reads only the check's loaded configuration and the database list its autodiscovery last produced. It never connects to the database or runs SQL. A database outside the monitoring scope and a database that does not exist are both answered as not found.

### MATCH-04 — Fail when the monitoring scope is unknown

When database autodiscovery is on and its database list cannot be read, the check answers with an error, never with not found.

### MATCH-05 — Match again before executing

A query request checks MATCH-01 to MATCH-04 on its check before connecting. When the check no longer serves the target, the run fails as target not found.

## Running the query

### QUERY-01 — Connect as the check, on a connection of the run's own

Each run opens one database connection with its check's connection settings, including its user, authentication, and TLS settings, to the database the target selects. The connection is used only by that run and is closed when the run ends. A run never takes, or waits for, a connection the check uses for monitoring.

### QUERY-02 — Run in one read-only transaction

Every statement of a run executes in one read-only transaction. The transaction is rolled back when the run ends, whatever its outcome.

### QUERY-03 — Fix the output settings

Before it describes the query, the integration sets these settings for the run's transaction only:

- client encoding: `UTF8`
- `TimeZone`: `UTC`
- `DateStyle`: `ISO, MDY`
- `IntervalStyle`: `postgres`
- `bytea_output`: `hex`
- `extra_float_digits`: `1`

The run's statements see these values. The check's monitoring connections keep their own settings.

Why: These settings give PostgreSQL fields a consistent text representation in the result files (intake INPUT-03, INPUT-04).

### QUERY-04 — Bound the statement time

The integration sets the transaction's statement timeout to the time left until the run time limit (TIME-01), or to the instance's remote query timeout when that is set and shorter. The timeout is at least 1 ms. The instance setting can shorten a run's time on the database, never lengthen it.

### QUERY-05 — Evaluate the query once

The integration first describes the query's result without evaluating it, then evaluates it exactly once, streaming its records with `COPY (<query>) TO STDOUT WITH (FORMAT CSV, NULL '\N')`. Both steps use the query text exactly as received. Text that is not exactly one query fails when it is described, before anything is evaluated or uploaded.

### QUERY-06 — Report database errors by their condition

When the database rejects the query, fails while running it, or refuses the connection, the failure message gives the error's SQLSTATE code and condition name, such as `42501 insufficient_privilege`. It never includes the database's message text. A statement timeout fails the run as a timeout, and a cancellation as cancelled (CANCEL-01).

## Describing the columns

### DESC-01 — Describe the result before reading any record

The integration reads the result's column names and column types, with their type modifiers, from the description of the query (QUERY-05). It does this before any record is read, including for a result with no rows.

### DESC-02 — Name each column's types

For each column, the database type name is the type catalog's formatted name of the column's described type with its type modifier, such as `numeric(10,2)` or `character varying(20)`. The logical type comes from the column type, as in the annex. Types the annex does not list have the logical type vendor.

### PG-01 — Reject PostgreSQL composite and array columns

Before uploading anything, the integration fails the query when a result column has a composite type (named or anonymous) or an array type, as reported by the database's type catalog. The error names the column and suggests expanding its fields into separate columns or converting it to JSON or JSONB.

### DESC-03 — Reject results a descriptor cannot carry

Before uploading anything, the integration fails the query when its result:

- has no columns;
- has more columns than the column limit;
- has two columns with the same name, which the error names; or
- needs a schema, and its encoded schema is larger than the schema size limit.

### DESC-04 — Register the descriptor before evaluating the query

The integration registers the descriptor with intake before it evaluates the query. The descriptor gives the PostgreSQL upload format, the schema choice, the Agent's hostname as the Agent reports it, and the columns in result order with their names, database type names, and logical types.

## Building pages

### SIZE-01 — Size each page by its result file

The integration closes a page before its estimated result file would exceed the result file size target. The estimate includes the file's header and schema, and the column names and JSON punctuation that every row repeats in the result file. It counts each record's uploaded bytes plus the per-row column names and punctuation. It does not decode or convert values.

The estimate can fall short, for example for values that need escaping in JSON. A file that ends up larger than the target is still accepted, up to intake's result file cap (intake PAGE-04).

### SIZE-02 — Split a page that intake reports as oversized

When intake reports that a page's result file exceeds its cap (intake PAGE-05), the integration uploads a smaller page under the same page index, holding the first half of the rejected page's records, rounded down. The records it left out start the next page. The query is not run again. When intake reports a page of one record as oversized, the run fails as a row too large.

### SIZE-03 — Upload records as the database wrote them

A page holds complete records, exactly as the COPY output wrote them, in result order. The integration never decodes, converts, or reorders values. A line break inside a quoted value does not end a record. When the COPY output ends inside a record, the run fails.

### SIZE-04 — Bound each record

When a record grows larger than the row size limit, the run fails as a row too large, without reading the rest of the record.

### SIZE-05 — Represent an empty result

A result with no rows uploads one page with no records, with the schema when it is requested (intake OUTPUT-05), and finalizes with a count of one.

### SIZE-06 — Stay within the run's limits

Before uploading a page, the integration fails the run as a result too large when:

- the page would exceed the page count limit; or
- the estimated result files of the run's pages so far, with this one, would exceed the total result size limit.

## Uploading pages

### UPLOAD-01 — Upload pages one at a time, in order

The integration uploads one run's pages one at a time, in page index order starting at 0. Each page's record offset is the number of rows in all earlier pages. It sends the next page only after intake acknowledges the previous one.

### UPLOAD-02 — Declare each page

Each page upload declares its page index, exact uncompressed byte length, row count, and record offset, and sends a fixed-length body (intake PAGE-01).

### UPLOAD-03 — Send the same page on every attempt

Every attempt of one page sends the same page index, declared values, and uncompressed bytes. Retries resend the compressed body made for the first attempt. Intake accepts a repeated page without reading it again (intake RETRY-02).

Why: An attempt whose acknowledgement was lost may have been recorded, so its retry must match it exactly to succeed.

### UPLOAD-04 — Retry requests that can still succeed

The integration retries a descriptor registration, page upload, or finalize as follows:

- **Intake is at capacity (intake PAGE-02):** retried until the run time limit.
- **A transport failure, an attempt that ended without an answer (UPLOAD-05), or another error intake marks as retryable:** retried up to the attempts limit; the run then fails as an upload failure.
- **An error intake marks as not retryable:** not retried; the run fails as an upload failure whose message gives intake's error code, except for an oversized page (SIZE-02).

Waits between attempts grow exponentially, with jitter, from the initial to the maximum [backoff](#limits). No attempt starts after the run time limit.

### UPLOAD-05 — Bound each attempt

An attempt ends without an answer when:

- connecting takes longer than the connect time limit;
- sending the body makes no progress for the send stall limit; or
- the attempt takes longer than its attempt time limit.

Why: The page attempt time limit is longer than intake's request time for a page, so intake answers every page attempt before the integration gives up on it.

### UPLOAD-06 — Send requests only to the upload address

Every intake request goes to the address the core Agent adds to the delivery instructions (Agent INPUT-05), with the operation's path appended. The integration follows the Agent's proxy configuration, verifies intake's TLS certificate, and never follows a redirect: a redirect answer fails the run as an upload failure.

Why: Every intake request carries the Agent's API key (UPLOAD-07), which a redirect could send to another host.

### UPLOAD-07 — Authenticate with the Agent's API key alone

Every intake request carries the Agent's API key and no other credential (intake AUTH-01).

### UPLOAD-08 — Compress page bodies

The integration compresses each page with gzip at the fastest level, and sends it with `Content-Encoding: gzip`. It sends a page uncompressed when compressing does not make it smaller. Compression does not block the run's other work while it runs. When intake answers that it does not accept the encoding, the integration sends that page and the run's later pages uncompressed. This fallback is not counted as a retry attempt (UPLOAD-04).

Why: The public link to intake is slower than intake's processing of unscanned pages, so fewer bytes on the wire shorten each upload. Result CSV usually compresses well.

## Finishing the run

### FINISH-01 — Finalize with the number of pages intake accepted

After the last page, the integration finalizes the session with the number of pages intake accepted (intake FINISH-01), retrying as in UPLOAD-04. Intake accepts a repeated finalize (intake FINISH-05).

### FINISH-02 — Report success only after finalizing

The integration answers success only after intake has confirmed the finalize. The answer carries no upload ID, counts, or totals (Agent OUT-02).

### ABORT-01 — Abort the upload of a failed run

When a run that passed request validation fails, the integration aborts its upload session (intake ABORT-01), including after the run time limit. The abort is bounded by the abort time limit. An abort failure is logged and never changes the run's answer. The integration never aborts a session after its finalize succeeded.

## Time and cancellation

### TIME-01 — Bound the run by its time limit

The run time limit starts when the integration receives the query request. It covers matching, connecting, describing, evaluating, uploading, retries, and finalizing, but not the abort. When the limit passes, the run stops reading and uploading, fails as a timeout, and aborts its session (ABORT-01).

### CANCEL-01 — Stop a cancelled run

When the Agent cancels a run (Agent RUN-04) or unschedules its check (Agent RUN-03), the integration:

- asks the database to cancel the run's statement, bounded by the cancel request time limit, which also stops a statement that has not yet returned its first record; and
- stops reading and uploading.

The run fails as cancelled and aborts its session (ABORT-01).

### CANCEL-02 — Refuse requests on an unscheduled check

A check that is being unscheduled answers every new match check and query request with a cancelled error, without parsing it.

### CANCEL-03 — Tear the check down only after its runs end

When a check is unscheduled while runs are in progress, it releases its resources only after the last run has ended. Cancelling runs never interrupts the check's monitoring queries.

## Errors and observability

### OBS-01 — Answer with one stable code and a safe message

Every failure answer carries exactly one code from the annex and a message that says what failed. Messages never contain the query text, result values, credentials, connection strings, or the text of a driver exception. Unexpected failures carry the internal error code and a fixed message.

### OBS-02 — Carry the run's trace to intake

When the query request carries a trace context, every intake request of the run carries it in the Datadog trace headers `x-datadog-trace-id`, `x-datadog-parent-id`, and `x-datadog-sampling-priority`. A request without a trace context carries no trace headers.

### OBS-03 — Log without data

Every log line about a run carries its crawl, task, and upload IDs. Logs never contain the query text, result values, credentials, or connection strings. Each acknowledged page is logged at debug level with its index, row count, uncompressed and sent byte counts, encoding (`gzip` or `identity`), compression and upload times in milliseconds, and whether gzip was tried but not kept because the page did not get smaller.

## Configuration

### CONFIG-01 — Let an instance shorten remote query time

The instance option `remote_queries.timeout_ms` shortens the statement timeout of remote queries on that instance (QUERY-04). It is unset by default, so the run time limit applies. When set, it is a number of milliseconds, at least 1.

## Performance

### PERF-01 — Frame records at 50 MiB/s

On one CPU core of an idle EC2 `m6gd.4xlarge`, the integration reads and frames COPY output into pages at 50 MiB/s or faster, measured over a run of at least 1 GiB against a database on the same host and a stub intake that answers at once. The target bounds the median of five runs.

## Scalability

### SCALE-01 — Keep monitoring unaffected

While runs are in progress on a check, the check's scheduled runs keep their collection interval and use no connection a run holds.

### SCALE-02 — Keep runs independent

Runs on one check, or on different checks, never wait on one another.

## Resource use

### RES-01 — Hold at most one page per run

While a page uploads, the integration reads no COPY output. A run holds in memory at most:

- one page and its compressed body (UPLOAD-08);
- the record in progress; and
- one block of COPY output.

The memory a run uses is at most twice the result file size target plus the row size limit, whatever the result's total size. A compressed body larger than its page is never kept.

### RES-02 — Use one database connection per run

A run holds exactly one database connection, from connecting until it ends (QUERY-01).

## Operations

| Operation | Caller | Does |
|---|---|---|
| Resolve | Agent | Says whether this check serves the target (MATCH-01 to MATCH-04) |
| Execute | Agent | Runs the query and uploads its result (MATCH-05 to FINISH-02) |

The integration uses these intake operations:

| Intake operation | Integration uses it to |
|---|---|
| Register descriptor | Register the columns before evaluating the query (DESC-04) |
| Upload page | Upload each page (UPLOAD-01 to UPLOAD-05, UPLOAD-08) |
| Finalize | Finish the upload (FINISH-01) |
| Abort | Stop the upload of a failed run (ABORT-01) |

## Limits

| Limit | Bounds | Value |
|---|---|---|
| Run time limit | One run, from the request to the finalize | The delivery instructions' query time limit |
| Result file size target | The size each result file aims for, best effort (SIZE-01) | The delivery instructions' result file size |
| Row size, page count, total result size, column, schema size limits | As named | The delivery instructions' limits |
| Statement timeout | The run's statements on the database | The time left in the run, or the instance's remote query timeout when shorter; at least 1 ms |
| Attempts | Attempts of one request for failures other than capacity | 5 |
| Backoff | Wait between attempts | 100 ms, doubling up to 5 s, with jitter |
| Connect time | Connecting to intake, per attempt | 10 s |
| Send stall | Time sending a request body may make no progress | 30 s |
| Page attempt time | One page upload attempt | 6 minutes |
| Other attempt time | One descriptor, finalize, or abort attempt | 30 s |
| Abort time | One abort, including its retries | 10 s |
| Cancel request time | One request to the database to cancel the run's statement | 5 s |

## Verification

Each item is checked at one layer. Performance and resource-use items are checked both by opt-in tests on the machine the Performance section names and on a deployed Agent.

| Layer | Items | Dependencies |
|---|---|---|
| Unit | REQ-01, REQ-02, MATCH-01, MATCH-02, MATCH-03, SIZE-01, SIZE-03, SIZE-04, OBS-01, CONFIG-01 | none |
| Check with Postgres and a stub intake | REQ-03, MATCH-04, MATCH-05, QUERY-01, QUERY-02, QUERY-03, QUERY-04, QUERY-05, QUERY-06, DESC-01, DESC-02, PG-01, DESC-03, DESC-04, SIZE-02, SIZE-05, SIZE-06, UPLOAD-01, UPLOAD-02, UPLOAD-03, UPLOAD-04, UPLOAD-05, UPLOAD-06, UPLOAD-07, UPLOAD-08, FINISH-01, FINISH-02, ABORT-01, TIME-01, CANCEL-01, CANCEL-02, CANCEL-03, OBS-02, OBS-03, SCALE-01, SCALE-02, RES-02 | a local Postgres; a stub intake that decodes gzip pages and can accept, refuse, stall, redirect, refuse the encoding, or report a page as oversized; an HTTP proxy; a short run time limit |
| Quality, opt-in | PERF-01, RES-01 | EC2 `m6gd.4xlarge`; a local Postgres; a stub intake |
| Deployed Agent | PERF-01, RES-01 confirmed end to end | staging Agent with a Postgres database and the staging intake; Agent memory metrics |

## Open questions

1. QUERY-01: should a check bound its concurrent runs, to protect the customer database? If so, what limit, and do extra runs wait or fail?
2. QUERY-06: is the SQLSTATE enough for users, or may messages of some error classes, such as syntax errors, be included?
3. OBS-02: besides passing the trace context, should the integration emit its own spans for its phases, and to which trace intake?

## Annex: logical types

The logical type of each column (DESC-02), by its column type:

| Column type | Logical type |
|---|---|
| `boolean` | boolean |
| `smallint`, `integer`, `bigint`, `oid` | integer |
| `numeric` | decimal |
| `real`, `double precision` | float |
| `text`, `character varying`, `character`, `"char"`, `name`, `uuid` | string |
| `date`, `time`, `time with time zone`, `timestamp`, `timestamp with time zone`, `interval` | temporal |
| `json`, `jsonb` | json |
| `bytea` | binary |
| Any other type, including `money`, `inet`, `cidr`, `macaddr`, enums, and extension types | vendor |

## Annex: failure codes

| Code | Failure |
|---|---|
| `invalid_request` | The request failed REQ-01 or REQ-02 |
| `target_not_found` | The check no longer serves the target (MATCH-05) |
| `target_unavailable` | The check's monitoring scope cannot be determined (MATCH-04) |
| `credentials_unavailable` | The Agent has no API key (REQ-03) |
| `connection_failed` | The database refused or dropped the connection (QUERY-06) |
| `query_failed` | The database rejected the query or failed while running it (QUERY-06) |
| `unsupported_column` | A column has a composite or array type (PG-01) |
| `invalid_columns` | The result has no columns, too many, or duplicate names (DESC-03) |
| `schema_too_large` | The schema is larger than the schema size limit, or leaves no room in a result file (DESC-03) |
| `row_too_large` | A record exceeds the row size limit, or a one-record page is oversized (SIZE-02, SIZE-04) |
| `result_too_large` | The result exceeds the page count or total result size limit (SIZE-06) |
| `upload_failed` | Intake rejected a request, or retries ran out (UPLOAD-04, UPLOAD-06) |
| `timeout` | The run time limit or the statement timeout passed (QUERY-06, TIME-01) |
| `cancelled` | The Agent cancelled the run or unscheduled the check (CANCEL-01, CANCEL-02) |
| `internal_error` | Any other failure (OBS-01) |
