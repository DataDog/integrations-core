# Metric Category Map — TRANSACTION LOGS (Db2 `MON_GET_TRANSACTION_LOG`)

Raw input for the IBM Db2 fidelity plan. Maps the **transaction-log** metric category
(log space used/available/utilization, log reads/writes/timing, secondary logs, log
buffer, archiving, log-to-redo / recovery footprint) to the equivalents Postgres and MySQL
emit, and proposes concrete `ibm_db2.*` metrics.

Scope boundary: this category is the Db2 analog of Postgres **WAL** (`pg_stat_wal`,
`pg_stat_archiver`, control-checkpoint WAL-byte deltas, `pg_ls_waldir`) and MySQL **binlog +
InnoDB redo log** (`mysql.binlog.*`, `mysql.innodb.{log_*,lsn_*,os_log_*}`). HADR log-shipping
lag/congestion lives in the **HADR/replication** category
(`_research/map-hadr-replication.md`) even though a few HADR log-wait columns are physically
present in `MON_GET_TRANSACTION_LOG` — those are cross-referenced (not double-mapped) below.

## Sources & provenance

- **Primary Db2 source: `MON_GET_TRANSACTION_LOG(member)`** — the modern, supported 12.1
  table function. Pass `-1` = current member, `-2` = all members. Returns **one row per
  member**; on a single-partition non-pureScale system that is exactly one row. Full 56-column
  schema captured live on **DB2/LINUXX8664 12.1.4.0**:
  `_research/_raw/02-monget-key-columns.txt` **L1456–L1513** (cited per-column below as
  "live L####"). The catalog cross-reference is `db2-monget-catalog-2.md` (function listed at
  56 cols, L16/L1456 in the DESCRIBE dump).
- **SYSIBMADM cross-check views** (live-confirmed present, `_research/_raw/03-sysibmadm-objects.txt`):
  `LOG_UTILIZATION` (L37), `MON_TRANSACTION_LOG_UTILIZATION` (L48), `SNAPDETAILLOG` (L66, legacy),
  `MON_DB_SUMMARY` (L43). Prefer the `MON_GET_TRANSACTION_LOG` table function over these views
  (the views are thin wrappers / legacy snapshots and offer no extra signal vs the function).
- **Existing integration code** already collects a 4-metric subset:
  `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py:95-98`
  (`TRANSACTION_LOG_TABLE`, columns `log_reads, log_writes, total_log_available, total_log_used`)
  submitted in `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:414-441`
  (`query_transaction_log`). It is wired into the per-run query list at `ibm_db2.py:72`.
- Postgres metric catalog: `/home/bits/dd/integrations-core/postgres/metadata.csv`.
  MySQL metric catalog: `/home/bits/dd/integrations-core/mysql/metadata.csv`.
  Existing Db2 catalog: `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`.

## Critical units note (load-bearing — get this right)

The existing code at `ibm_db2.py:418-432` treats `TOTAL_LOG_USED` and `TOTAL_LOG_AVAILABLE`
as **bytes** and divides by `block_size = 4096` to report **4 KiB blocks**:

```python
block_size = 4096
used = tlog['total_log_used']                      # BYTES per Db2 doc
self.gauge(self.m('log.used'), used / block_size)  # -> emitted in 4KiB BLOCKS
available = tlog['total_log_available']            # BYTES, or -1 for "infinite logging"
if available == -1:
    utilized = 0                                   # infinite log space -> util pinned to 0
else:
    utilized = used / available * 100              # PERCENT
    available /= block_size                        # -> emitted in 4KiB BLOCKS
```

Confirmed against IBM docs: `TOTAL_LOG_USED` / `TOTAL_LOG_AVAILABLE` are documented in **bytes**
(general Db2 12.1 knowledge — verify; the IBM doc URLs are cited inline in the code). The
`available == -1` sentinel = **infinite active log space** (`LOGSECOND = -1`); the integration
pins `log.utilized = 0` in that case (a known fidelity gap — see notes). `*_TOP` high-water
columns (`SEC_LOG_USED_TOP`, `TOT_LOG_USED_TOP`) are also bytes. `*_TIME` columns are
**milliseconds**. `LOG_READS`/`LOG_WRITES`/`NUM_LOG_*_IO` are page/IO **counts** (monotonic).

> Recommendation for new metrics: emit raw **byte** gauges (`...space.used.bytes` etc.) rather
> than perpetuating the 4 KiB-block unit, while KEEPING the existing `ibm_db2.log.used`/
> `.available` (blocks) for backward compatibility. Reconcile in metadata.csv.

## Monitor-switch gating

`MON_GET_TRANSACTION_LOG` works with default switches; the live monitor config
(`_research/_raw/04-monitor-config.txt`) shows `mon_req_metrics=BASE`, `mon_obj_metrics=EXTENDED`
— sufficient. Log space, reads/writes, and timing counters are **always populated** (they are
core logger counters, not gated by request/object metric switches). No version gating needed
for the columns in the live 12.1.4 dump; flag any column NOT in the live dump as version-gated
(none of the proposed-core columns fall in that bucket — all 56 are live-confirmed).

---

# MAPPING TABLE

Legend: type = Datadog submission type (`gauge` / `count`=monotonic_count / `rate`).
metadata.csv `metric_type` column uses `gauge`/`count`/`rate` accordingly. All metrics carry
base instance tags (`db`, `database_hostname`, `database_instance`, version tag) plus `member`
(MON_GET fan-out dimension). Proposed prefix namespace: **`ibm_db2.log.*`** (extends the
existing `ibm_db2.log.{used,available,utilized,reads,writes}`).

## A. Log SPACE — used / available / utilization / high-water / secondary

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.control.checkpoint_delay_bytes` (WAL bytes since checkpoint — closest "log volume in flight"); no direct mysql analog | `MON_GET_TRANSACTION_LOG.TOTAL_LOG_USED` (live L1460, BIGINT bytes) | `ibm_db2.log.used` (**existing**, blocks) **+ new** `ibm_db2.log.space.used` (bytes) | gauge | byte (new) / block (existing) | db, member | EXISTING emits 4KiB blocks (`ibm_db2.py:422`). Add raw-byte variant. |
| (no pg/mysql analog — Db2 active-log headroom) | `MON_GET_TRANSACTION_LOG.TOTAL_LOG_AVAILABLE` (live L1459, BIGINT bytes; **`-1` = infinite logging**) | `ibm_db2.log.available` (**existing**, blocks) **+ new** `ibm_db2.log.space.available` (bytes) | gauge | byte / block | db, member | EXISTING (`ibm_db2.py:434`). `-1` sentinel must be handled (skip metric or emit -1, don't divide). |
| (no direct analog; conceptually mysql InnoDB redo "checkpoint_age" fullness, pg has none) | derived: `TOTAL_LOG_USED / TOTAL_LOG_AVAILABLE * 100` (live L1460/L1459) | `ibm_db2.log.utilized` (**existing**) | gauge | percent | db, member | EXISTING (`ibm_db2.py:435`). **Fidelity gap:** pinned to `0` under infinite logging (`available==-1`, `ibm_db2.py:429`). Consider NULL/skip instead. |
| (no analog) | `MON_GET_TRANSACTION_LOG.TOT_LOG_USED_TOP` (live L1462, BIGINT bytes, high-water) | `ibm_db2.log.space.used.max` | gauge | byte | db, member | High-water mark of total log space used since activation. Capacity-planning signal. |
| (no analog; ~mysql binlog growth pressure) | `MON_GET_TRANSACTION_LOG.SEC_LOG_USED_TOP` (live L1461, BIGINT bytes) | `ibm_db2.log.secondary.used.max` | gauge | byte | db, member | High-water of SECONDARY (overflow) log space used. Sustained >0 ⇒ undersized `LOGPRIMARY`/`LOGFILSIZ`. |
| (no analog) | `MON_GET_TRANSACTION_LOG.SEC_LOGS_ALLOCATED` (live L1463, BIGINT count) | `ibm_db2.log.secondary.allocated` | gauge | file | db, member | # secondary log files currently allocated. Pair with `LOGSECOND` db cfg (`db2-config-settings.md`). >0 = burning into secondaries now. |
| `postgresql.wal_count` (count of WAL files on disk) — loose analog | `MON_GET_TRANSACTION_LOG.NUM_LOGS_AVAIL_FOR_RENAME` (live L1493, INTEGER) | `ibm_db2.log.files.reusable` | gauge | file | db, member | # log files available for rename/reuse. Low value ⇒ log space pressure. |

## B. Log THROUGHPUT — reads / writes / IO counts

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.log_write_requests` / `postgresql.wal.write` (WAL buffer writes) | `MON_GET_TRANSACTION_LOG.LOG_WRITES` (live L1466, BIGINT, log **pages** written by logger) | `ibm_db2.log.writes` (**existing**) | count | page (existing unit `write`) | db, member | EXISTING (`ibm_db2.py:441`). Counts log PAGES written to disk. |
| `mysql.innodb.os_log_written` (bytes)/no pg analog | `MON_GET_TRANSACTION_LOG.LOG_READS` (live L1464, BIGINT, log **pages** read by logger) | `ibm_db2.log.reads` (**existing**) | count | page (existing unit `read`) | db, member | EXISTING (`ibm_db2.py:438`). Log pages read (rollback/recovery/cur-commit). |
| `mysql.innodb.log_writes` (physical writes to redo) | `MON_GET_TRANSACTION_LOG.NUM_LOG_WRITE_IO` (live L1468, BIGINT) | `ibm_db2.log.write_io` | count | operation | db, member | # physical write I/O requests to log (vs pages). Pair with `LOG_WRITES` for avg pages/IO. |
| (no analog) | `MON_GET_TRANSACTION_LOG.NUM_LOG_READ_IO` (live L1469, BIGINT) | `ibm_db2.log.read_io` | count | operation | db, member | # physical read I/O requests against log. |
| (no analog — partial-page rewrite churn) | `MON_GET_TRANSACTION_LOG.NUM_LOG_PART_PAGE_IO` (live L1470, BIGINT) | `ibm_db2.log.partial_page_io` | count | operation | db, member | # partial log-page write I/Os. High ratio ⇒ inefficient small commits. |

## C. Log TIMING — latency of log I/O (wait-time decomposition)

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.wal.write_time` (ms spent writing WAL) | `MON_GET_TRANSACTION_LOG.LOG_WRITE_TIME` (live L1467, BIGINT ms) | `ibm_db2.log.write_time` | count | millisecond | db, member | Cumulative ms in log write I/O. Divide by `NUM_LOG_WRITE_IO` (in-app) for avg write latency. |
| `postgresql.wal.sync_time` (loose — fsync side) / no mysql analog | `MON_GET_TRANSACTION_LOG.LOG_READ_TIME` (live L1465, BIGINT ms) | `ibm_db2.log.read_time` | count | millisecond | db, member | Cumulative ms in log read I/O. |

## D. Log BUFFER — buffer hits / buffer-full stalls

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.innodb.log_waits` (log buffer too small ⇒ wait) / `postgresql.wal.buffers_full` (WAL buffer full ⇒ forced write) | `MON_GET_TRANSACTION_LOG.NUM_LOG_BUFFER_FULL` (live L1471, BIGINT) | `ibm_db2.log.buffer_full` | count | event | db, member | **Direct analog of both** `innodb.log_waits` and `wal.buffers_full`. # times log buffer filled forcing a flush. Tune `LOGBUFSZ`. High-signal. |
| (no analog — log-buffer read-hit ratio) | `MON_GET_TRANSACTION_LOG.NUM_LOG_DATA_FOUND_IN_BUFFER` (live L1472, BIGINT) | `ibm_db2.log.data_found_in_buffer` | count | hit | db, member | # log reads satisfied from log buffer w/o disk (cur-commit/rollback). Pair w/ `LOG_READS` for a log-buffer hit ratio. |

## E. CURRENTLY-COMMITTED (cur-commit) log reads — readers avoiding lock waits

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no analog — Db2 currently-committed semantics) | `MON_GET_TRANSACTION_LOG.CUR_COMMIT_TOTAL_LOG_READS` (live L1481, BIGINT) | `ibm_db2.log.cur_commit.reads.total` | count | read | db, member | Total log reads for currently-committed (CC) processing. |
| (no analog) | `MON_GET_TRANSACTION_LOG.CUR_COMMIT_DISK_LOG_READS` (live L1480, BIGINT) | `ibm_db2.log.cur_commit.reads.disk` | count | read | db, member | CC log reads that hit DISK (cache miss). High disk fraction ⇒ CC overhead. |
| (no analog) | `MON_GET_TRANSACTION_LOG.CUR_COMMIT_LOG_BUFF_LOG_READS` (live L1482, BIGINT) | `ibm_db2.log.cur_commit.reads.buffer` | count | read | db, member | CC log reads served from log buffer. `total - disk - buffer` breakdown. |

## F. RECOVERY / REDO footprint — recovery-time-objective signals

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.control.redo_delay_bytes` (WAL bytes since redo point) / `mysql.innodb.checkpoint_age` (redo bytes to apply) | `MON_GET_TRANSACTION_LOG.LOG_TO_REDO_FOR_RECOVERY` (live L1474, BIGINT bytes) | `ibm_db2.log.to_redo_for_recovery` | gauge | byte | db, member | **Strong analog** of `innodb.checkpoint_age` / `control.redo_delay_bytes`. Amount of log (bytes) that crash recovery would have to replay NOW. Direct RTO/`SOFTMAX`/`PAGE_AGE_TRGT` signal. |
| (no analog — dirty-page log retention) | `MON_GET_TRANSACTION_LOG.LOG_HELD_BY_DIRTY_PAGES` (live L1475, BIGINT bytes) | `ibm_db2.log.held_by_dirty_pages` | gauge | byte | db, member | Bytes of log held (un-truncatable) because dirty pages aren't yet flushed. Drives page-cleaner aggressiveness tuning. |
| (no analog — long-running-txn log pinning) | `MON_GET_TRANSACTION_LOG.APPLID_HOLDING_OLDEST_XACT` (live L1473, BIGINT = application handle) | `ibm_db2.log.oldest_xact.appl_handle` (**tag/info, not a metric**) | — | — | db, member | App handle pinning the oldest open transaction's log. Use as a **tag/event attribute** or skip; not a numeric metric. Join to `MON_GET_CONNECTION` to name the culprit. Loose analog of pg `before_xid_wraparound` pressure source. |
| (no analog — in-doubt 2PC txns) | `MON_GET_TRANSACTION_LOG.NUM_INDOUBT_TRANS` (live L1494, BIGINT) | `ibm_db2.log.indoubt_transactions` | gauge | transaction | db, member | # in-doubt (prepared-but-unresolved 2PC) transactions. >0 = operator attention; blocks log truncation. Service-check candidate. |

## G. ACTIVE LOG WINDOW — log-file extent positions (LSN/LSO numbering)

These are log-file sequence numbers / LSNs — emit as **gauges** (monotonic-ish, can jump on
archive/restore). Mostly useful for dashboards/derived rates, not alerting.

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| (no analog) | `MON_GET_TRANSACTION_LOG.FIRST_ACTIVE_LOG` (live L1476, BIGINT) | `ibm_db2.log.active.first` | gauge | — | db, member | First (oldest) active log file number. |
| (no analog) | `MON_GET_TRANSACTION_LOG.LAST_ACTIVE_LOG` (live L1477, BIGINT) | `ibm_db2.log.active.last` | gauge | — | db, member | Last active log file number. `last - first + 1` = active-window file count. |
| (no analog) | `MON_GET_TRANSACTION_LOG.CURRENT_ACTIVE_LOG` (live L1478, BIGINT) | `ibm_db2.log.active.current` | gauge | — | db, member | Log file currently being written. |
| `postgresql.wal_receiver.received_timeline` (loose — log chain/timeline) | `MON_GET_TRANSACTION_LOG.LOG_CHAIN_ID` (live L1489, BIGINT) | `ibm_db2.log.chain_id` | gauge | — | db, member | Log chain (incremented on restore/rollforward). Timeline analog. |
| `mysql.innodb.lsn_current` (current LSN) | `MON_GET_TRANSACTION_LOG.CURRENT_LSN` (live L1491, BIGINT) | `ibm_db2.log.lsn.current` | gauge | — | db, member | Current log sequence number. Derive write rate from deltas. |
| `mysql.innodb.lsn_flushed` (loose) | `MON_GET_TRANSACTION_LOG.CURRENT_LSO` (live L1490, BIGINT) | `ibm_db2.log.lso.current` | gauge | — | db, member | Current log-stream offset. |
| `mysql.innodb.lsn_last_checkpoint` (loose — oldest unflushed) | `MON_GET_TRANSACTION_LOG.OLDEST_TX_LSN` (live L1492, BIGINT) | `ibm_db2.log.lsn.oldest_tx` | gauge | — | db, member | LSN of oldest uncommitted transaction. `current - oldest_tx` ≈ open-txn log span. |

## H. ARCHIVING — log archive status & failures (the `pg_stat_archiver` analog)

This is the Db2 analog of `postgresql.archiver.archived_count`/`.failed_count`. Db2 has TWO
archive methods (`LOGARCHMETH1`/`LOGARCHMETH2`). `*_STATUS` are SMALLINT enums; `*_NEXT_LOG_*`
and `*_FIRST_FAILURE` are log-number/timestamp-ish BIGINTs.

| pg / mysql analog | Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.archiver.failed_count` (archiving health) | `MON_GET_TRANSACTION_LOG.ARCHIVE_METHOD1_STATUS` (live L1483, SMALLINT enum) | `ibm_db2.log.archive.method1.status` | gauge | — | db, member, **method:1** | Enum (0=success/idle, nonzero=failure states — verify enum, general Db2 12.1 knowledge). Best mapped to a **service-check** + gauge. Tag method or emit `.method1.`/`.method2.`. |
| `postgresql.archiver.failed_count` | `MON_GET_TRANSACTION_LOG.ARCHIVE_METHOD2_STATUS` (live L1486, SMALLINT enum) | `ibm_db2.log.archive.method2.status` | gauge | — | db, member, **method:2** | Same; only meaningful if `LOGARCHMETH2` configured. |
| `postgresql.archiver.archived_count` (which log is being archived ≈ progress) | `MON_GET_TRANSACTION_LOG.METHOD1_NEXT_LOG_TO_ARCHIVE` (live L1484) / `METHOD2_NEXT_LOG_TO_ARCHIVE` (live L1487, BIGINT) | `ibm_db2.log.archive.method{1,2}.next_log` | gauge | — | db, member, method | Next log file pending archive. Gap vs `CURRENT_ARCHIVE_LOG` = archive backlog. |
| (no analog — archive failure marker) | `MON_GET_TRANSACTION_LOG.METHOD1_FIRST_FAILURE` (live L1485) / `METHOD2_FIRST_FAILURE` (live L1488, BIGINT) | (info/event, not a metric) | — | — | db, member, method | First-failure marker (log/timestamp). Surface as event/log attribute. |
| `postgresql.archiver.archived_count` (loose — current archive progress) | `MON_GET_TRANSACTION_LOG.CURRENT_ARCHIVE_LOG` (live L1479, BIGINT) | `ibm_db2.log.archive.current_log` | gauge | — | db, member | Log file currently being archived. |

## I. LOG EXTRACTION (12.1 — CDC / log-reader / IIDR-style streaming)

`LOG_EXTRACTION_*` (live L1497–L1513) is a large 12.1 family for the integrated log-extraction
/ replication-capture engine. **No pg/mysql analog** (closest is pg logical-decoding spill
counters `postgresql.replication_slot.spill_*`, but the mechanism differs). Recommend
collecting only if log extraction is in use (gate behind a config flag); otherwise these read 0.
Selected high-value columns:

| Db2 source: fn + exact column (live ref) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|
| `LOG_EXTRACTION_PROCESSED_BYTES` (L1497, BIGINT) | `ibm_db2.log.extraction.processed_bytes` | count | byte | db, member | Bytes of log processed by extraction. |
| `LOG_EXTRACTION_PROCESSING_TIME` (L1498, BIGINT ms) | `ibm_db2.log.extraction.processing_time` | count | millisecond | db, member | Time spent processing. |
| `LOG_EXTRACTION_WRITTEN_BYTES` (L1499) / `LOG_EXTRACTION_WRITE_TIME` (L1500) | `ibm_db2.log.extraction.written_bytes` / `.write_time` | count | byte / millisecond | db, member | Output volume + write time. |
| `LOG_EXTRACTION_CUR_COMMIT_READS` (L1503) / `_TIME` (L1504) | `ibm_db2.log.extraction.cur_commit.reads` / `.time` | count | read / millisecond | db, member | CC reads driven by extraction. |
| `LOG_EXTRACTION_ROLLBACK_READS` (L1501) / `_TIME` (L1502) | `ibm_db2.log.extraction.rollback.reads` / `.time` | count | read / millisecond | db, member | Rollback reads driven by extraction. |
| `LOG_EXTRACTION_DISK_SPACE_USED_TOTAL` (L1505) / `_TOP` (L1506, BIGINT bytes) | `ibm_db2.log.extraction.disk_space_used` / `.disk_space_used.max` | gauge | byte | db, member | Spill space used by extraction + high-water. ~ pg slot spill_bytes analog. |
| `LOG_EXTRACTION_NUM_DISK_FULL` (L1510, BIGINT) | `ibm_db2.log.extraction.disk_full` | count | event | db, member | # times extraction spill disk filled. Alert signal. |
| `LOG_EXTRACTION_STATUS` (L1511, SMALLINT enum) | `ibm_db2.log.extraction.status` | gauge | — | db, member | Extraction engine status enum. Service-check candidate. |
| `LOG_EXTRACTION_LAST_EXTRACTED_LOG` (L1507) / `_PROCESSED_LSO` (L1508) / `_PROCESSED_LSN` (L1509) | `ibm_db2.log.extraction.last_log` / `.processed_lso` / `.processed_lsn` | gauge | — | db, member | Position markers; derive extraction lag vs `CURRENT_LSN`. |
| `LAST_LOG_VALIDATION_ERROR` (L1513, BIGINT) | (info/event) | — | — | db, member | Last log validation error marker. Surface as event. |

---

# CROSS-REFERENCED (do NOT map here — belongs to HADR/replication category)

These columns are **physically present** in `MON_GET_TRANSACTION_LOG` (live dump) but are
HADR log-shipping congestion signals; they are mapped in `_research/map-hadr-replication.md`
(see its §"primary source `MON_GET_HADR`"). Avoid double-counting — pick ONE source function
(prefer `MON_GET_HADR` for the HADR category since it also carries the standby-side columns).

| Db2 column (also in MON_GET_TRANSACTION_LOG, live ref) | Where it belongs | HADR-map reference |
|---|---|---|
| `LOG_HADR_WAIT_TIME` (live L1495, BIGINT ms) | HADR/replication (log-write congestion from HADR sync) | `map-hadr-replication.md` L78 |
| `LOG_HADR_WAITS_TOTAL` (live L1496, BIGINT count) | HADR/replication | `map-hadr-replication.md` L79 |

> Note: `MON_GET_HADR` itself does not expose `LOG_HADR_WAIT_TIME`/`_WAITS_TOTAL`; those two
> live ONLY in `MON_GET_TRANSACTION_LOG`. The HADR map (L45, L78-79) explicitly points back
> here for them. Decision for the plan: collect these two from `MON_GET_TRANSACTION_LOG` (this
> query) but **document/dashboard them under HADR**. They are the only TRANSACTION_LOG columns
> that semantically straddle both categories.

---

# Db2-NATIVE metrics worth adding (no pg/mysql analog) — priority picks

Ranked by signal value for an ops dashboard:

1. **`ibm_db2.log.buffer_full`** (`NUM_LOG_BUFFER_FULL`) — actually IS the pg/mysql analog (D)
   but Db2 surfaces it cleanly; top tuning signal for `LOGBUFSZ`. **(high)**
2. **`ibm_db2.log.to_redo_for_recovery`** (`LOG_TO_REDO_FOR_RECOVERY`) — crash-recovery RTO
   gauge; analog of `innodb.checkpoint_age`. **(high)**
3. **`ibm_db2.log.held_by_dirty_pages`** (`LOG_HELD_BY_DIRTY_PAGES`) — page-cleaner / log-
   truncation health. **(high)**
4. **`ibm_db2.log.secondary.{used.max,allocated}`** (`SEC_LOG_USED_TOP`, `SEC_LOGS_ALLOCATED`)
   — running into secondary/overflow logs ⇒ undersized log config. **(high)**
5. **`ibm_db2.log.indoubt_transactions`** (`NUM_INDOUBT_TRANS`) — 2PC operator-attention +
   blocks truncation. **(high — also service-check)**
6. **`ibm_db2.log.archive.method{1,2}.status`** (`ARCHIVE_METHOD{1,2}_STATUS`) — closest Db2
   thing to `pg_stat_archiver` failures; archiving health / service-check. **(high)**
7. **`ibm_db2.log.cur_commit.reads.{total,disk,buffer}`** (`CUR_COMMIT_*_LOG_READS`) —
   currently-committed-isolation overhead; Db2-specific. **(medium)**
8. **`ibm_db2.log.{write,read}_io`** + `partial_page_io` (`NUM_LOG_*_IO`) — pages-per-IO
   efficiency. **(medium)**
9. **`ibm_db2.log.data_found_in_buffer`** (`NUM_LOG_DATA_FOUND_IN_BUFFER`) — log-buffer
   read-hit ratio. **(medium)**
10. **`ibm_db2.log.files.reusable`** (`NUM_LOGS_AVAIL_FOR_RENAME`) — log-recycling headroom.
    **(low/medium)**
11. LSN/LSO position gauges (G) — dashboards / derived rates only. **(low)**
12. `LOG_EXTRACTION_*` family (I) — only if log extraction/CDC is configured. **(low, gated)**

---

# pg/mysql log metrics with NO Db2 equivalent (flag as gaps)

| pg / mysql metric | why no Db2 equivalent |
|---|---|
| `postgresql.wal.records` / `postgresql.wal.full_page_images` | Db2 logs at log-page/byte granularity, not WAL "records"/"full-page-image" granularity. No per-record or FPI counter in `MON_GET_TRANSACTION_LOG`. Closest is `LOG_WRITES` (pages). **No analog.** |
| `postgresql.wal.bytes` (total WAL generated, bytes) | No cumulative "log bytes generated" counter exposed; `LOG_WRITES` is pages, `TOTAL_LOG_USED` is point-in-time space. Derive bytes ≈ `LOG_WRITES × log_page_size(4096)` (approx; partial pages skew it). **Partial/derived only.** |
| `postgresql.wal.sync` (count of WAL fsyncs) | No separate fsync-count column; Db2 folds sync into `LOG_WRITE_TIME`/`NUM_LOG_WRITE_IO`. **No direct analog.** |
| `postgresql.wal_age` (age in seconds of oldest WAL file) | No log-file-age column; would require filesystem inspection (agent co-located) like pg's `_collect_wal_metrics`. **No SQL analog.** |
| `postgresql.wal_size` / `postgresql.wal_count` (on-disk WAL bytes/file count) | Partial: `NUM_LOGS_AVAIL_FOR_RENAME` (reusable count) + `SEC_LOGS_ALLOCATED` exist, but no total on-disk-bytes/file-count of the whole log path. `TOTAL_LOG_AVAILABLE+USED` ≈ configured active size, not on-disk total. **Partial analog.** |
| `mysql.innodb.os_log_pending_{writes,fsyncs}` / `pending_log_{flushes,writes}` | No "pending log I/O" depth counters in `MON_GET_TRANSACTION_LOG`. **No analog.** |
| `mysql.binlog.cache_use` / `cache_disk_use` (binlog statement cache spill) | Db2 has no statement-level binlog cache concept; logging is page-buffer based. Loose conceptual cousin is `NUM_LOG_BUFFER_FULL`, already mapped. **No direct analog.** |
| `postgresql.replication_slot.spill_*` / `stream_*` / `total_*` | Logical-decoding slot accounting; Db2 has no replication slots. Nearest is the `LOG_EXTRACTION_*` family (I) but semantics differ. **No direct analog (use extraction family if applicable).** |
| `postgresql.recovery_prefetch.*` | PG recovery-prefetch instrumentation; Db2 recovery is not exposed via these counters. **No analog.** |

---

# Implementation notes for the plan

1. **Reuse one query, widen the column list.** Replace `TRANSACTION_LOG_TABLE_COLUMNS`
   (`queries.py:95`, currently 4 cols) with the full set above. The function returns one row
   per member; keep `member` as a tag (current code uses `MON_GET_TRANSACTION_LOG(-1)` =
   current member only — switch to `-2` for MPP/pureScale to fan out, then tag by `MEMBER`).
   Migrate to the declarative QueryExecutor `columns` style per `code-mysql-metrics.md` §5/§11
   and `code-postgres-metrics.md` §1.B (preferred over the hand-rolled cursor in
   `ibm_db2.py:414-441`).
2. **Units discipline.** `TOTAL_LOG_USED/AVAILABLE`, `*_TOP`, `LOG_*_DISK_SPACE_USED*` = **bytes**;
   `*_TIME` = **ms**; `LOG_READS/WRITES`, `NUM_LOG_*_IO` = **counts/pages**. Existing
   `ibm_db2.log.{used,available}` emit 4 KiB **blocks** (`ibm_db2.py:418-432`) — keep for
   back-compat, add byte-native siblings. Every new metric needs a row in
   `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` (it currently has only the 5
   `ibm_db2.log.*` rows).
3. **Infinite logging.** Guard `TOTAL_LOG_AVAILABLE == -1` (LOGSECOND=-1): do NOT divide;
   skip `log.utilized`/`log.available` or emit a sentinel. Current code pins util=0
   (`ibm_db2.py:429`) — a fidelity gap to document.
4. **Service checks** (mirroring pg/mysql patterns, not metrics): `NUM_INDOUBT_TRANS > 0`,
   `ARCHIVE_METHOD{1,2}_STATUS != ok`, `LOG_EXTRACTION_STATUS != ok` are good service-check
   or monitor candidates.
5. **Graceful degradation.** Wrap the query so a privilege error (needs SYSMON/DBADM-class
   authority) degrades to a warning, per `code-postgres-metrics.md` §2 error-handling and
   `code-mysql-metrics.md` §11.4.
6. **Config gating.** Core space/throughput/timing columns: always on. `LOG_EXTRACTION_*`
   (family I) and per-method archive detail: gate behind an opt-in flag (analogous to pg
   `collect_wal_metrics` / mysql `extra_status_metrics`).
7. **Cross-category coordination.** `LOG_HADR_WAIT_TIME`/`LOG_HADR_WAITS_TOTAL` are emitted
   here (only source) but documented under HADR (`map-hadr-replication.md`); coordinate metric
   naming with that map (suggest `ibm_db2.hadr.log_wait_time` / `.log_waits` to keep them in
   the HADR namespace even though sourced from this query).
