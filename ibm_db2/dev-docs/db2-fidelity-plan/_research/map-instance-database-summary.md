# Metric Category Map — INSTANCE / DATABASE SUMMARY (Db2 fidelity plan)

Raw input for the IBM Db2 fidelity plan. Maps the **instance/database-summary** metric
category to the analogs Postgres and MySQL emit, and proposes concrete `ibm_db2.*` metrics
to reach parity. This is the "is the instance/database alive, how long has it been up, how
many connections, and the top-line summary ratios" category — the cheapest, lowest-cardinality,
always-collectable probe that anchors a dashboard's status row.

Server under test: **DB2/LINUXX8664 12.1.4.0** (`_raw/01-version-and-monget-functions.txt:4,9`).

## Scope of THIS category (and what is delegated to sibling maps)

In-scope here:
- **Instance / DB status** (active / quiesced / standby) → service checks + a numeric status gauge.
- **Uptime** (instance start time → seconds up). The Db2 analog of `postgresql.uptime`.
- **Identity / version / edition / topology** surfaced as metadata + low-cardinality tags
  (from `MON_GET_INSTANCE`, `SYSIBMADM.ENV_INST_INFO`, `ENV_PROD_INFO`, `SYSIBM.SYSVERSIONS`).
- **Instance-wide connection & agent-pool summary** counts that belong to the instance, not a
  single connection: `MON_GET_INSTANCE` agent/gateway counts, `TOTAL_CONNECTIONS`, `CON_LOCAL_DBASES`.
- **Database-level summary ratios / liveness** that are roll-ups (not per-object): backup age,
  the `MON_DB_SUMMARY` summary ratios (avg pool hit ratio, rows-read-per-rows-returned ratio,
  cat/pkg cache hit ratios, sort overflow %, CPU utilization), `db.count`-style "databases monitored".
- A numeric **"running"/`can_connect`** liveness gauge (Db2 analog of `postgresql.running`).

Delegated to sibling maps (cross-referenced, NOT re-mapped here to avoid double-counting):
- **Per-connection** throughput / wait detail and the application-count gauges
  (`appls_cur_cons`, `appls_in_db2`, `connections_top`) → `map-connections-applications.md`
  (`MON_GET_CONNECTION`, `MON_GET_DATABASE` connection cols). NOTE the *existing* check already
  emits `connection.active/max/total` + `application.active/executing` from `MON_GET_DATABASE`;
  those live in the connections map. This map only adds the **instance-wide** agent/gateway counts
  and `con_local_dbases`.
- **Commits / rollbacks / rows / SQL-statement-mix** counters → `map-rows-throughput.md`
  (`MON_GET_DATABASE` ROWS_*, *_SQL_STMTS, TOTAL_APP_COMMITS, ...).
- **Locks / deadlocks / lock escalations** → `map-locking-concurrency.md`.
- **Buffer pool reads/hit ratios per pool** → `map-bufferpool.md` (the *per-pool* breakdown). The
  *single instance-wide summary* avg-hit-ratio from `MON_DB_SUMMARY` is included here as a summary
  ratio (it is a roll-up, not per-pool).
- **Transaction-log space/IO** → `map-transaction-logs.md`.
- **Tablespace storage** → `map-tablespace-storage.md`. **HADR** → `map-hadr-replication.md`.
- **Sort/hash spills** → `map-sorting-hashing.md`. **Memory pools/sets** → (memory map; catalog-2 §7-8).

## Sources & provenance

- **`MON_GET_INSTANCE(member)`** — 24 cols, live DESCRIBE `_raw/02-monget-key-columns.txt`
  **L2451-2474** (cited "live L####"). One row per member; `-1`=current, `-2`=all. The cheapest
  instance-health + in-band version probe. Catalog cross-ref: `db2-monget-catalog-2.md` §3.
- **`MON_GET_DATABASE(member)`** — 515 cols, live `_raw/02-monget-key-columns.txt` **L16-530**.
  Summary-relevant cols: `DB_STATUS` (L17), `DB_ACTIVATION_STATE` (L18), `DB_CONN_TIME` (L19),
  `CATALOG_PARTITION` (L20), `LAST_BACKUP` (L21), `TOTAL_CONS` (L23), `TOTAL_SEC_CONS` (L24).
- **`MON_GET_TRANSACTION_LOG(member)`** — only referenced for cross-links; full map in
  `map-transaction-logs.md` (`_raw/02...` L1456-1513).
- **`SYSIBMADM.MON_DB_SUMMARY`** — pre-built summary view, live-confirmed present
  (`_raw/03-sysibmadm-objects.txt:43`). IBM-curated database roll-up with ready-made summary
  ratios (avg pool hit %, rows-read/returned, cache hit %, CPU utilization, etc.). Columns below
  are general Db2 12.1 knowledge — verify against a live `DESCRIBE SELECT * FROM SYSIBMADM.MON_DB_SUMMARY`.
- **`SYSIBMADM.ENV_INST_INFO`** — version/build/topology view, live-confirmed present
  (`_raw/03:30`). Live values: `service_level='DB2 v12.1.4.0'`, `bld_level='s2602211313'`,
  `fixpack_num=0`, `release_num='02050110'`, `num_members=1` (`db2-editions-versions.md:154-156`).
- **`SYSIBMADM.ENV_PROD_INFO`** — edition/license view, live-confirmed present (`_raw/03:31`). Live
  values: `installed_prod='DEC'`, `prod_release='12.1'`, `license_type='COMMUNITY'`
  (`db2-editions-versions.md:162-164`). Filter `LICENSE_INSTALLED='Y'`.
- **`SYSIBM.SYSVERSIONS`** — packed version int, live `versionnumber=12010400` (VVRRMMFF),
  `version_timestamp=2026-06-13-...` (`db2-editions-versions.md:147-148`).
- **`TABLE(SYSPROC.ENV_GET_INST_INFO())`** — table-function form of ENV_INST_INFO (no view
  dependency); `SELECT service_level, fixpack_num` (`db2-editions-versions.md:158`).
- **Driver fallback (already in check):** `ibm_db.get_db_info(conn, ibm_db.SQL_DBMS_VER)` → raw
  `MM.mm.uuuu` (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28`,
  parsed `ibm_db2.py:109-125`).

Monitor-switch gating (`_raw/04-monitor-config.txt`): `mon_req_metrics=BASE`, `mon_obj_metrics=EXTENDED`
— the summary counters in this category are populated under BASE; none of these metrics need EXTENDED.

> **Current integration code refs.** The check already calls `MON_GET_INSTANCE(-1)` (selecting only
> `total_connections`, `queries.py:15-17`, submitted `ibm_db2.py:127-131`) and `MON_GET_DATABASE(-1)`
> (`queries.py:20-40`, submitted `ibm_db2.py:133-190`), and derives `ibm_db2.backup.latest` from
> `last_backup` (`ibm_db2.py:176-181`). It emits the `ibm_db2.status` service check from `db_status`
> (`ibm_db2.py:137`, map `utils.py:13-20`) and `ibm_db2.can_connect` (`ibm_db2.py:580-589`). **There is
> no uptime metric, no numeric status gauge, no version/edition tag, no instance-wide agent-pool counts,
> and no summary-ratio metrics.** Almost everything proposed below is "add columns to the two SELECTs the
> check already runs" + one new `ENV_INST_INFO`/`MON_DB_SUMMARY` query.

---

## 0. TL;DR for the implementer

1. **Highest-value, lowest-cost adds:** `ibm_db2.uptime` (derive from `MON_GET_INSTANCE.DB2START_TIME`)
   and `ibm_db2.running`/`ibm_db2.db2_status` (numeric liveness gauge). Both are dashboard "status row"
   anchors with direct pg analogs (`postgresql.uptime`, `postgresql.running`) and zero added cost — one
   already-run function (`MON_GET_INSTANCE`).
2. **Version/edition as tags, not metrics:** surface `service_level`/`installed_prod`/`license_type`
   via `set_metadata` + low-cardinality instance tags (`db2_version`, `db2_edition`), mirroring
   Postgres `postgresql_version:` tag. Do NOT emit version as a metric value.
3. **Instance-wide agent-pool counts** (`AGENTS_REGISTERED`, `IDLE_AGENTS`, `NUM_COORD_AGENTS`,
   `AGENTS_CREATED_EMPTY_POOL`, gateway counts) have **no pg/mysql analog** but are genuinely
   Db2-native saturation signals — add them (gauges + a couple monotonic_count).
4. **`MON_DB_SUMMARY` is an IBM-curated free summary view** — one cheap query yields ready-made
   summary ratios (avg pool hit %, rows-read/returned ratio, cache hit %, CPU utilization). Prefer it
   over hand-computing the same ratios from `MON_GET_DATABASE`, but VERIFY column names live first.
5. **`db.count` analog:** Db2 is single-database-per-connection, so the natural analog is "databases
   active in this instance" (`MON_GET_INSTANCE.CON_LOCAL_DBASES`) — emit as a low-value gauge or skip.

---

## 1. MAPPING TABLE — instance/database summary

Legend: type = Datadog submission type (`gauge`/`count`(=monotonic_count in code)/`rate`). Unit per
`metadata.csv` vocabulary. Tags listed are *in addition to* the global base tags
(`db:<DBNAME>`, user `tags`, and proposed `database_hostname`/`database_instance`/`db2_member`).

### 1A. Status / liveness / uptime (the status-row anchors)

| pg/mysql analog | Db2 source: fn/view + exact column | proposed `ibm_db2.<name>` | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| `postgresql.running` (gauge, =1 when up); `mysql.can_connect` SC | derived: 1 if `MON_GET_INSTANCE` query succeeds (or `_conn` not None) | `ibm_db2.running` | gauge | (none) | — | Db2 analog of `postgresql.running`. Emit `1` after a successful instance probe; never emit on failure (the absence drives a monitor). Pairs with existing `ibm_db2.can_connect` SC. Already have the SC; this adds the numeric gauge. (general Db2 — derive in code) |
| `postgresql.uptime` (gauge, second) | `MON_GET_INSTANCE.DB2START_TIME` (live L2453) → `(CURRENT TIMESTAMP - DB2START_TIME)` seconds | `ibm_db2.uptime` | gauge | second | — | **Top priority add.** Compute in SQL: `TIMESTAMPDIFF`-style or fetch `DB2START_TIME` + a `CURRENT TIMESTAMP` column (the check already adds `current timestamp AS current_time` in `query_database`, `ibm_db2.py:113`) and diff in Python like `backup.latest` does (`ibm_db2.py:176-181`). Instance-level (no `db` granularity needed). live L2453 confirms column. |
| `postgresql.running` per-instance; no direct mysql | `MON_GET_INSTANCE.DB2_STATUS` (live L2452; VARCHAR(12): ACTIVE/QUIESCE_PEND/QUIESCED) → numeric map | `ibm_db2.instance.status` | gauge | (none) | `db2_status:<value>` | New numeric liveness gauge for the *instance* (0=ACTIVE, 1=QUIESCE_PEND, 2=QUIESCED, ...). Complements the **existing** `ibm_db2.status` SERVICE CHECK which is from the *database* `DB_STATUS` (`MON_GET_DATABASE`, `ibm_db2.py:137`). Consider also an `ibm_db2.instance.can_connect`-style SC from `DB2_STATUS`. live L2452. |
| `postgresql.running` (db-level); part of existing `ibm_db2.status` SC | `MON_GET_DATABASE.DB_STATUS` (live L17; VARCHAR(16)) + `DB_ACTIVATION_STATE` (live L18) | `ibm_db2.database.status` | gauge | (none) | `db_status:<value>`,`db` | Numeric companion to the existing `ibm_db2.status` SC (map ACTIVE→0 etc. via `DB_STATUS_MAP`, `utils.py:13-20`). `DB_ACTIVATION_STATE` (EXPLICIT/IMPLICIT) is a useful tag. live L17-18. |
| `postgresql.db.count` (gauge, item) | `MON_GET_INSTANCE.CON_LOCAL_DBASES` (live L2456, BIGINT) | `ibm_db2.databases.active` | gauge | item | — | Db2 analog of "databases available/monitored". `CON_LOCAL_DBASES` = # local databases with active connections. Lower-fidelity than pg (pg counts all DBs in cluster; Db2 monitors one DB per connection) — emit as a coarse instance gauge or skip. live L2456. |
| `ibm_db2.backup.latest` (already exists) | `MON_GET_DATABASE.LAST_BACKUP` (live L21, TIMESTAMP) vs `CURRENT TIMESTAMP` | `ibm_db2.backup.latest` (existing) | gauge | second | `db` | **Already implemented** (`ibm_db2.py:176-181`); listed for completeness — it is a database-summary liveness signal. Returns `-1` when no backup recorded. live L21. |
| (no direct analog) | `MON_GET_DATABASE.DB_CONN_TIME` (live L19, TIMESTAMP) vs `CURRENT TIMESTAMP` | `ibm_db2.database.uptime` | gauge | second | `db` | Database-activation uptime (since first connect / activation), distinct from instance uptime. Db2-native; optional. live L19. |

### 1B. Instance-wide connection & agent-pool summary (Db2-native; mostly no pg/mysql analog)

These belong to the **instance**, not an individual connection (which is `map-connections-applications.md`).
All from `MON_GET_INSTANCE` (live L2451-2474) unless noted.

| pg/mysql analog | Db2 source: column | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `mysql.net.connections` (rate)/ pg `numbackends` (loosely) | `TOTAL_CONNECTIONS` (live L2457, BIGINT) | `ibm_db2.instance.connections.total` | gauge | connection | — | Current connections to the **instance** (across all local DBs). Distinct from existing `ibm_db2.connection.active` which is `MON_GET_INSTANCE.total_connections` already (NOTE: existing check selects `total_connections` here, `queries.py:16` — confirm whether that column is `TOTAL_CONNECTIONS`; the existing `connection.active` already maps it). Avoid double-emitting; reconcile with connections map. live L2457. |
| no analog | `AGENTS_REGISTERED` (live L2458) | `ibm_db2.agents.registered` | gauge | agent | — | Total DB2 agents (EDUs) registered. Saturation signal vs `MAXAGENTS`/`max_coordagents`. |
| no analog | `AGENTS_REGISTERED_TOP` (live L2459) | `ibm_db2.agents.registered_top` | gauge | agent | — | High-water mark. |
| no analog | `IDLE_AGENTS` (live L2460) | `ibm_db2.agents.idle` | gauge | agent | — | Agents in pool idle. |
| no analog | `AGENTS_FROM_POOL` (live L2461) | `ibm_db2.agents.from_pool` | count | agent | — | monotonic_count: agents assigned from the pool (pool-reuse efficiency). |
| no analog | `AGENTS_CREATED_EMPTY_POOL` (live L2462) | `ibm_db2.agents.created_empty_pool` | count | agent | — | **Pool-pressure signal** (analogous in spirit to `mysql.performance.threads_created`): agents created because the pool was empty. |
| `mysql` thread analog (loose) | `NUM_COORD_AGENTS` (live L2463) | `ibm_db2.agents.coord` | gauge | agent | — | Coordinator agents (≈ active connections doing work). |
| no analog | `COORD_AGENTS_TOP` (live L2464) | `ibm_db2.agents.coord_top` | gauge | agent | — | High-water mark of coordinator agents. |
| no analog | `AGENTS_STOLEN` (live L2465) | `ibm_db2.agents.stolen` | count | agent | — | monotonic_count: agents reassigned between applications. |
| no analog | `GW_CUR_CONS` (live L2467) | `ibm_db2.gateway.connections.current` | gauge | connection | — | DRDA gateway current connections (federation/DRDA only; usually 0). |
| no analog | `GW_TOTAL_CONS` (live L2466) | `ibm_db2.gateway.connections.total` | count | connection | — | monotonic_count. |
| no analog | `GW_CONS_WAIT_HOST` (live L2468) | `ibm_db2.gateway.connections.waiting_host` | gauge | connection | — | Gateway conns waiting on host. |
| no analog | `GW_CONS_WAIT_CLIENT` (live L2469) | `ibm_db2.gateway.connections.waiting_client` | gauge | connection | — | Gateway conns waiting on client. |
| no analog | `NUM_GW_CONN_SWITCHES` (live L2470) | `ibm_db2.gateway.connection_switches` | count | connection | — | monotonic_count. |

Also relevant at instance scope but already partly emitted from `MON_GET_DATABASE` (reconcile in
connections map): `MON_GET_DATABASE.TOTAL_CONS` (live L23 → existing `ibm_db2.connection.total`),
`TOTAL_SEC_CONS` (live L24, secondary/coordinator connections — currently unmapped; candidate
`ibm_db2.connection.secondary.total` count), `CONNECTIONS_TOP` (live L22 → existing `ibm_db2.connection.max`).

### 1C. Identity / version / edition / topology (emit as METADATA + low-cardinality TAGS, not metric values)

| pg/mysql analog | Db2 source: view/fn + column | proposed surface | notes / version-gating |
|---|---|---|---|
| pg `postgresql_version:<raw>` tag + `set_metadata('version')` | `SYSIBMADM.ENV_INST_INFO.SERVICE_LEVEL` ('DB2 v12.1.4.0') OR `MON_GET_INSTANCE.SERVICE_LEVEL` (live L2472) | tag `db2_version:12.1.4.0` + `set_metadata('version', ..., scheme='parts')` | The check ALREADY sets `version.*` metadata via the driver (`ibm_db2.py:109-125`). Add the richer in-band string and a `db2_version` instance tag (mirror pg). `MON_GET_INSTANCE.SERVICE_LEVEL` avoids a second query. live L2472. |
| pg `system_identifier:` tag (loose) | `MON_GET_INSTANCE.PRODUCT_NAME` (live L2471, e.g. 'DB2 v12.1.4.0'), `SERVER_PLATFORM` (live L2473, 'LINUXX8664') | tags `db2_product`, `db2_platform` (optional) | Low cardinality. live L2471,2473. |
| no direct analog (mysql `dbms_flavor` tag, `mysql.py:320`) | `SYSIBMADM.ENV_PROD_INFO.INSTALLED_PROD` ('DEC'), `LICENSE_TYPE` ('COMMUNITY'), `PROD_RELEASE` ('12.1') WHERE `LICENSE_INSTALLED='Y'` | tags `db2_edition:DEC`, `db2_license:COMMUNITY` | Mirror mysql's `dbms_flavor`. Filter `LICENSE_INSTALLED='Y'`; never enumerate codes (`db2-editions-versions.md:94,108`). Edition gates feature availability (BLU/pureScale). |
| pg version gating (`if version >= V*`) | `SYSIBM.SYSVERSIONS.VERSIONNUMBER` (packed 12010400 = VVRRMMFF) | internal gating input (not emitted) | Use for capability gating exactly like pg's `V*` constants. `IF versionnumber >= 12010000 THEN <12.1-only>`. (`db2-editions-versions.md:147-150`). |
| no analog | `SYSIBMADM.ENV_INST_INFO.NUM_MEMBERS` (=1), `IS_INST_PARTITIONABLE` (=0), `NUM_DBPARTITIONS` (=1) | tag `db2_member`/`db2_members` count; topology gate | Single-member non-DPF live. Drives whether per-member fan-out + GBP metrics matter. (`db2-editions-versions.md:170-174`). |
| no analog | `MON_GET_INSTANCE.DB2START_TIME` (live L2453) | (used for `ibm_db2.uptime` above) | — |

### 1D. Database summary ratios — from `SYSIBMADM.MON_DB_SUMMARY` (IBM-curated roll-up)

`MON_DB_SUMMARY` is a single-row-per-member summary view (live present `_raw/03:43`). It pre-computes
the ratios that pg/mysql dashboards show on a summary tile. **All column names below are general Db2 12.1
knowledge — VERIFY with `DESCRIBE SELECT * FROM SYSIBMADM.MON_DB_SUMMARY` before coding.** Where a column
exists equivalently in `MON_GET_DATABASE` (already-run function), prefer computing it from there to save a
round-trip; `MON_DB_SUMMARY` is the convenience alternative.

| pg/mysql analog | `MON_DB_SUMMARY` column (verify) | proposed `ibm_db2.<name>` | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| `postgresql.buffer_hit` (rate); existing `ibm_db2.bufferpool.hit_percent` (per-pool) | `GW_TOTAL_CONS`→ no; `TOTAL_BP_HIT_RATIO_PERCENT` | `ibm_db2.summary.bufferpool.hit_percent` | gauge | percent | — | Instance-wide avg BP hit ratio (vs the per-`bufferpool` metric in `map-bufferpool.md`). Summary tile. (verify column name) |
| `postgresql.buffer_hit` data/index split | `DATA_BP_HIT_RATIO_PERCENT`, `INDEX_BP_HIT_RATIO_PERCENT` | `ibm_db2.summary.bufferpool.data.hit_percent`, `...index.hit_percent` | gauge | percent | — | Summary-level data/index hit ratios. (verify) |
| no direct analog (efficiency ratio) | `ROWS_READ_PER_ROWS_RETURNED` (or compute `ROWS_READ/ROWS_RETURNED`) | `ibm_db2.summary.rows_read_per_returned` | gauge | row | — | Classic Db2 health ratio: rows scanned per row returned (high ⇒ missing index / table scans). Can compute from `MON_GET_DATABASE.ROWS_READ`/`ROWS_RETURNED` (live L90/L91). (verify) |
| no analog | `PKG_CACHE_HIT_RATIO_PERCENT` | `ibm_db2.summary.pkg_cache.hit_percent` | gauge | percent | — | Package-cache hit ratio (≈ pg plan-cache health). Compute from `PKG_CACHE_INSERTS`/`PKG_CACHE_LOOKUPS` (live L147/L148) if column absent. (verify) |
| no analog | `CAT_CACHE_HIT_RATIO_PERCENT` | `ibm_db2.summary.cat_cache.hit_percent` | gauge | percent | — | Catalog-cache hit ratio. Compute from `CAT_CACHE_INSERTS`/`CAT_CACHE_LOOKUPS` (live L145/L146). (verify) |
| no analog | `SORT_OVERFLOW_RATIO_PERCENT` / from `SORT_OVERFLOWS`/`TOTAL_SORTS` | `ibm_db2.summary.sort_overflow_percent` | gauge | percent | — | % sorts that spilled to disk (cross-ref `map-sorting-hashing.md`; the summary ratio belongs here). `SORT_OVERFLOWS`/`TOTAL_SORTS` live L113/L110. (verify) |
| `mysql.performance.cpu_time` (loose) | `AVG_CPU_UTILIZATION_PERCENT` or `TOTAL_CPU_TIME` | `ibm_db2.summary.cpu_utilization_percent` | gauge | percent | — | Engine CPU utilization roll-up. Db2 also exposes raw `MON_GET_DATABASE.TOTAL_CPU_TIME` (live L104, microseconds — verify unit). (verify) |
| `postgresql.commits`/`rollbacks` (rate) — roll-up form | `ACT_COMPLETED_TOTAL`, `APP_RQSTS_COMPLETED_TOTAL` | (delegate to `map-rows-throughput.md`) | — | — | — | The throughput counters belong to rows-throughput; only listed so the implementer knows `MON_DB_SUMMARY` carries them too. |

> **Decision guidance:** `MON_DB_SUMMARY` is attractive because IBM maintains the ratio math, but its
> column set has shifted across releases. The robust path is to compute the handful of summary ratios
> from `MON_GET_DATABASE` columns the check **already** (or will) fetch — no extra query, no view
> dependency, exact column names already captured live (L16-530). Use `MON_DB_SUMMARY` only if a live
> `DESCRIBE` confirms the columns on 12.1.4.

---

## 2. Db2-native metrics worth adding with NO pg/mysql analog (this category)

1. **Agent-pool saturation family** (§1B): `ibm_db2.agents.{registered,registered_top,idle,from_pool,
   created_empty_pool,coord,coord_top,stolen}`. This is the single most valuable Db2-native addition in
   this category — there is no Postgres/MySQL equivalent (their connection model differs), but
   `AGENTS_CREATED_EMPTY_POOL` / `IDLE_AGENTS` vs `NUM_COORD_AGENTS` is the canonical "is the agent pool
   sized right / am I thrashing agents" signal. All from `MON_GET_INSTANCE` (already-called function).
2. **DRDA gateway family** (§1B): `ibm_db2.gateway.connections.*`. Only meaningful for DRDA/federation
   servers (usually 0 on a plain server) — gate emission on `GW_TOTAL_CONS > 0` or a config flag to avoid
   noise. No pg/mysql analog.
3. **Instance vs database status split** (§1A): Db2 distinguishes *instance* status (`MON_GET_INSTANCE.
   DB2_STATUS`) from *database* status (`MON_GET_DATABASE.DB_STATUS`) and *activation state*
   (`DB_ACTIVATION_STATE`). pg/mysql have a single liveness notion. Worth surfacing both as numeric gauges
   + the existing SC.
4. **`db2_edition`/`db2_license` tags** (§1C): Db2's licensed-edition concept (DEC/COMMUNITY/AESE/...) has
   no pg analog; it gates which features (BLU/column-organized, pureScale, HADR multi-standby) are even
   present, so it is a valuable curated tag.
5. **`ibm_db2.databases.active`** (`CON_LOCAL_DBASES`): partial analog of `postgresql.db.count` but
   instance-scoped to active local databases; Db2-specific framing.
6. **Topology gauges** (optional): `ibm_db2.members` (from `ENV_INST_INFO.NUM_MEMBERS`) — 1 on the live
   single-member box; only interesting on DPF/pureScale. Mostly a tag, not a metric.

---

## 3. pg/mysql summary metrics with NO clean Db2 equivalent (flagged)

| pg/mysql metric | why no Db2 equivalent in this category | closest Db2 fallback |
|---|---|---|
| `postgresql.before_xid_wraparound` (gauge, transaction) | Db2 does **not** use transaction-ID wraparound / freezing (no MVCC XID horizon). No equivalent. | None. Db2's analogous "log space exhaustion" risk lives in `map-transaction-logs.md` (`TOTAL_LOG_USED`/`available`/`utilized`). |
| `postgresql.max_connections` / `percent_usage_connections` / `database_connections` / `percent_database_usage_connections` | These are computed against pg `max_connections` GUC. Db2's cap is `MAXAPPLS`/`max_connections` DB cfg + `max_coordagents` DBM cfg — a *config*, not a `MON_GET_*` column. | Compute `connections / MAXAPPLS * 100` from DB CFG (`db2-config-settings.md`); belongs to connections map. Not a MON_GET summary column. |
| `mysql.net.aborted_clients` / `aborted_connects` | No single Db2 instance-summary counter for aborted/failed connects. | `MON_GET_INSTANCE` has no abort counter; `TOTAL_CONNECT_AUTHENTICATIONS` failures are not split out at instance level. Partial: `MON_GET_DATABASE.FAILED_SQL_STMTS` (different concept). |
| `mysql.performance.threads_created`/`threads_cached`/`threads_connected`/`threads_running` | MySQL thread model. Db2's analog is the **agent** model. | Use the agent-pool family in §1B (`agents.created_empty_pool` ≈ `threads_created`; `agents.idle` ≈ `threads_cached`; `agents.coord` ≈ `threads_running`). Not 1:1 but semantically closest. |
| `mysql.performance.open_files` / `open_tables` | MySQL table-cache concept. | Db2 `MON_GET_DATABASE.FILES_CLOSED` (live L269) is a counter of files closed under pressure (inverse-ish signal); no "currently open files" gauge at instance summary. |
| `postgresql.archiver.*` (archived/failed count) | Log archiving status. | Delegated: `MON_GET_TRANSACTION_LOG.ARCHIVE_METHOD1_STATUS`/`METHOD1_FIRST_FAILURE` (`map-transaction-logs.md`, live L1483-1488). Not in this summary category. |
| `mysql.galera.*` / pg replication summary | Cluster/replication. | Delegated to `map-hadr-replication.md` (`MON_GET_HADR`). pureScale CF status via `SYSIBMADM.DB2_CF`. |

---

## 4. Proposed SQL (concrete, ready to adapt)

### 4.1 Instance summary (extends the existing `query_instance`, `queries.py:15-17`)

```sql
SELECT
    member,
    db2_status,
    db2start_time,
    (CURRENT TIMESTAMP) AS current_time,   -- for uptime diff in Python, like backup.latest
    total_connections,
    con_local_dbases,
    agents_registered,
    agents_registered_top,
    idle_agents,
    agents_from_pool,
    agents_created_empty_pool,
    num_coord_agents,
    coord_agents_top,
    agents_stolen,
    gw_cur_cons,
    gw_total_cons,
    gw_cons_wait_host,
    gw_cons_wait_client,
    num_gw_conn_switches,
    product_name,
    service_level,
    server_platform
FROM TABLE(MON_GET_INSTANCE(-1)) AS t
```
All columns confirmed live (`_raw/02...` L2451-2474). `-1` = current member; use `-2` + a `member` tag for
DPF/pureScale. Uptime = `(current_time - db2start_time).total_seconds()` (reuse the pattern at
`ibm_db2.py:176-181`).

### 4.2 Version / edition / topology (one-time-per-run; could be cached like mysql `GlobalVariables`)

```sql
-- identity + topology (view form)
SELECT service_level, bld_level, fixpack_num, release_num,
       num_members, is_inst_partitionable, num_dbpartitions
FROM SYSIBMADM.ENV_INST_INFO;            -- live values: 'DB2 v12.1.4.0','s2602211313',0,'02050110',1,0,1

-- edition / license
SELECT installed_prod, prod_release, license_type
FROM SYSIBMADM.ENV_PROD_INFO WHERE license_installed = 'Y';   -- live: 'DEC','12.1','COMMUNITY'

-- packed version int for gating (no view dependency)
SELECT versionnumber FROM SYSIBM.SYSVERSIONS;                 -- live: 12010400
```
Sources: `db2-editions-versions.md:154-156,162-164,147-148`. `ENV_GET_INST_INFO()` table-function form
is `SELECT service_level, fixpack_num FROM TABLE(SYSPROC.ENV_GET_INST_INFO())` (`:158`) if the view is
unavailable. Surface via `set_metadata` + tags; do not emit as metrics.

### 4.3 Database status / activation / uptime (extends existing `query_database`, `queries.py:20-40`)

```sql
SELECT
    db_status,            -- live L17  (existing service check input)
    db_activation_state,  -- live L18  (new tag)
    db_conn_time,         -- live L19  (new: ibm_db2.database.uptime)
    last_backup,          -- live L21  (existing ibm_db2.backup.latest)
    (CURRENT TIMESTAMP) AS current_time
    -- ... plus the throughput/lock/row columns already selected and those in sibling maps
FROM TABLE(MON_GET_DATABASE(-1)) AS t
```

### 4.4 Summary ratios (OPTIONAL — verify columns live first)

```sql
-- IBM-curated roll-up; VERIFY columns via DESCRIBE before relying on names
SELECT * FROM SYSIBMADM.MON_DB_SUMMARY;     -- live present (_raw/03:43)
```
Preferred robust alternative — compute ratios from `MON_GET_DATABASE` columns already fetched:
`pkg_cache_hit = (1 - PKG_CACHE_INSERTS/NULLIF(PKG_CACHE_LOOKUPS,0)) * 100` (live L147/L148),
`cat_cache_hit` from L145/L146, `rows_read_per_returned = ROWS_READ/NULLIF(ROWS_RETURNED,0)` (L90/L91),
`sort_overflow_pct = SORT_OVERFLOWS/NULLIF(TOTAL_SORTS,0)*100` (L113/L110).

---

## 5. Tagging model (this category)

- **Global base tags** (mirror pg/mysql; add to the check): `db:<DBNAME>` (already auto-added,
  `ibm_db2.py:48`), `database_hostname:<host>`, `database_instance:<id>` (new — mirror
  pg `add_core_tags`, `code-postgres-metrics.md` §5), and `db2_member:<n>` for DPF/pureScale when
  querying with `-2`.
- **Identity tags** (new, low cardinality): `db2_version:<x.y.z>`, `db2_edition:<code>`,
  `db2_license:<type>`, optional `db2_platform`, `db2_product`. Mirror pg `postgresql_version:` and
  mysql `dbms_flavor:`.
- **Status tags** (per-metric): `db2_status:<DB2_STATUS>` on `ibm_db2.instance.status`,
  `db_status:<DB_STATUS>` + `db_activation_state:<>` on `ibm_db2.database.status`.
- Instance-level summary metrics (uptime, agents.*, gateway.*) carry **no** `db` granularity beyond the
  global `db` tag (Db2's instance can host multiple DBs but this check connects to one).
- Metric hostname should be the resolved DB host (mirror pg `reported_hostname`), not the agent host.

---

## 6. Type / unit discipline (for metadata.csv rows)

- Monotonic lifetime counters (`AGENTS_FROM_POOL`, `AGENTS_CREATED_EMPTY_POOL`, `AGENTS_STOLEN`,
  `GW_TOTAL_CONS`, `NUM_GW_CONN_SWITCHES`) → submit `monotonic_count` → metadata.csv type `count`.
- Point-in-time gauges (`uptime`, all `*.status`, `agents.{registered,idle,coord,*_top}`,
  `gateway.connections.{current,waiting_*}`, `databases.active`, all `summary.*` ratios) → `gauge`.
- Units: `second` (uptime/database.uptime/backup.latest), `agent` (new unit; or reuse `connection`),
  `connection` (gateway/instance connections), `percent` (summary ratios), `item` (databases.active),
  `row` (rows_read_per_returned), none for `*.status`/`running`.
- Every new metric needs a row in `/home/bits/dd/integrations-core/ibm_db2/metadata.csv` with
  `integration=ibm_db2`, an orientation hint (e.g. `uptime` 0, `agents.created_empty_pool` -1,
  `summary.bufferpool.hit_percent` 1), and a description naming the source `MON_GET_*`/view + any gating.

---

## 7. Open verification items (hand to implementer)

1. **`MON_DB_SUMMARY` column names** — run `DESCRIBE SELECT * FROM SYSIBMADM.MON_DB_SUMMARY` on 12.1.4
   to confirm the ratio column names in §1D (marked verify). If they differ, compute from
   `MON_GET_DATABASE` columns (exact live names captured L16-530).
2. **`MON_GET_INSTANCE.total_connections` vs existing `ibm_db2.connection.active`** — the existing check
   already maps `total_connections` from this function (`queries.py:16`, `ibm_db2.py:131`). Confirm whether
   that is `TOTAL_CONNECTIONS` (live L2457) and reconcile so the proposed `ibm_db2.instance.connections.total`
   does not duplicate it. Likely keep the existing name and only ADD the agent/gateway/uptime columns.
3. **`TOTAL_CPU_TIME` unit** — `MON_GET_DATABASE.TOTAL_CPU_TIME` (live L104) is microseconds per general Db2
   convention (catalog-2 §4 flags `TOTAL_CPU_TIME` as us not ms) — verify before deriving a CPU % or rate.
4. **Service-check vs gauge** for instance status — decide whether to add an `ibm_db2.instance.status` SC
   (mirroring the existing DB-level `ibm_db2.status`) in addition to / instead of the numeric gauge.
5. **Caching the identity/version query** — fetch ENV_INST_INFO/ENV_PROD_INFO/SYSVERSIONS **once per run**
   (or once per connection) and cache, mirroring mysql `GlobalVariables` (`code-mysql-metrics.md` §8); these
   values rarely change and should not cost a round-trip every collection.
```
