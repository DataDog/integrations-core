# Map: FCM / pureScale Metric Category — IBM Db2 Fidelity Plan

Raw implementation input mapping the **fcm-purescale** metric category to the Datadog
`ibm_db2` integration. Scope per task:

1. **FCM (Fast Communications Manager)** — inter-member message/buffer/channel traffic on
   MPP (DPF) and pureScale clusters: `MON_GET_FCM`, `MON_GET_FCM_CONNECTION_LIST`, plus the
   embedded `FCM_*` columns that already appear inside `MON_GET_DATABASE` /
   `MON_GET_CONNECTION` / `MON_GET_SERVICE_SUBCLASS` / `MON_GET_WORKLOAD`.
2. **pureScale CF (Cluster Caching Facility)** — `MON_GET_CF`, `MON_GET_CF_CMD`,
   `MON_GET_CF_WAIT_TIME`, `SYSIBMADM.DB2_CF`, `SYSIBMADM.ENV_CF_SYS_RESOURCES`, plus the
   embedded `CF_WAIT_TIME` / `CF_WAITS` columns in the request-time functions.
3. **pureScale group buffer pool (GBP)** — `MON_GET_GROUP_BUFFERPOOL` (castout, cross
   member invalidation at the GBP-structure level). NOTE: the per-bufferpool GBP
   hit-ratios and `POOL_*_GBP_*` page counters are owned by the **bufferpool** category
   (`map-bufferpool.md` rows 69-70, 161-163); this doc covers the GBP-structure /
   castout-engine level and explicitly flags the overlap so the implementer does not
   double-map.

> **pureScale-only.** Every metric here is meaningful ONLY on a Db2 pureScale (shared-disk
> CF cluster) deployment; the FCM-channel metrics are additionally meaningful on Db2 DPF
> (MPP, shared-nothing). On the single-node live container (`DB2/LINUXX8664 12.1.4.0`,
> `_raw/01-version-and-monget-functions.txt` L4/L9) all of these functions EXIST but their
> CF/GBP counters return 0 rows or all-NULL/0. The bufferpool research confirms this:
> "On a single-node container ... the GBP columns are all NULL/0, so `group.*` paths are
> `# no cov`" (`map-bufferpool.md` L169). **Gate the entire category behind a pureScale /
> DPF detection probe and emit nothing on a non-clustered instance.**

## Provenance / how to read this doc

- "DESCRIBE dump" = `DESCRIBE SELECT * FROM TABLE(<fn>(...))`, captured live in
  `_raw/02-monget-key-columns.txt`. **Critical caveat:** that dump contains only 11
  functions (`MON_GET_DATABASE`, `_BUFFERPOOL`, `_TABLESPACE`, `_CONNECTION`,
  `_TRANSACTION_LOG`, `_TABLE`, `_INDEX`, `_HADR`, `_SERVICE_SUBCLASS`, `_WORKLOAD`,
  `_INSTANCE` — see `db2-monget-catalog-2.md` L13-19). The three headline functions for
  this category — **`MON_GET_FCM`, `MON_GET_CF`, `MON_GET_GROUP_BUFFERPOOL`** (and
  `MON_GET_CF_CMD`, `MON_GET_CF_WAIT_TIME`, `MON_GET_FCM_CONNECTION_LIST`) — are **NOT**
  in the DESCRIBE dump. They are all **confirmed present on the live server**
  (`_raw/01-version-and-monget-functions.txt`: `MON_GET_CF` L20, `MON_GET_CF_CMD` L21,
  `MON_GET_CF_WAIT_TIME` L22, `MON_GET_FCM` L30, `MON_GET_FCM_CONNECTION_LIST` L31,
  `MON_GET_GROUP_BUFFERPOOL` L32). Their column lists below are therefore **general Db2
  12.1 knowledge — verify** with a live `DESCRIBE` before coding (the live container is
  single-node so a DESCRIBE will still return the schema even though rows are empty).
- The embedded `FCM_*`, `FCM_TQ_*`, `FCM_MESSAGE_*`, `CF_WAIT_TIME`, `CF_WAITS`,
  `RECLAIM_WAIT_TIME`, `SPACEMAPPAGE_RECLAIM_WAIT_TIME`, and `*_GLOBAL` columns ARE
  empirically confirmed in the dump (grep of `_raw/02-monget-key-columns.txt`): they live
  in `MON_GET_DATABASE` (region L16-537), `MON_GET_CONNECTION` (L1030-1455),
  `MON_GET_SERVICE_SUBCLASS` (L1684-2061), and `MON_GET_WORKLOAD` (L2069-2446). Each
  appears 4x — once per function. These are marked **(confirmed in `_raw/02`)**.
- SQL type codes in the dump: `493 BIGINT`(8), `497 INTEGER`(4), `501 SMALLINT`(2),
  `449 VARCHAR`(n), `481 DOUBLE`(8), `393 TIMESTAMP`(26).
- Units convention (general Db2 monitor-element knowledge): `*_TIME` = **milliseconds**;
  `*_VOLUME` = **bytes**; `*_REQUESTS`/`*_SENDS_TOTAL`/`*_RECVS_TOTAL`/`*_WAITS*` = monotonic
  **counts**; CF resource sizes (`CURRENT_CF_*`, `*_SIZE`) = **4 KB pages or bytes** (verify
  per element). Recommended Datadog type: monotonic lifetime counter → `monotonic_count`
  (catalog `count`); point-in-time gauge → `gauge`.
- The **current** integration emits NONE of these except indirectly: it computes
  `ibm_db2.bufferpool.group.*.hit_percent` from `POOL_*_GBP_*` columns and guards them with
  `if <gbp>_reads_logical:` so they no-op off pureScale (`map-bufferpool.md` L69-70, L171;
  `ibm_db2.py:233,270,307,344,372`). There is **no** FCM, CF, castout, or GBP-structure
  metric today.
- Live monitor switches that gate population (`_raw/04-monitor-config.txt`):
  `mon_req_metrics=BASE`, `mon_obj_metrics=EXTENDED`. BASE request metrics are sufficient to
  populate the `FCM_*_WAIT_TIME` / `CF_WAIT_TIME` request-time families inside
  SERVICE_SUBCLASS/WORKLOAD/DATABASE. `MON_GET_FCM`/`MON_GET_CF`/`MON_GET_GROUP_BUFFERPOOL`
  populate regardless of switches (they read live CF/FCM engine counters).

---

## 0. pureScale / DPF detection (prerequisite gate — implement FIRST)

All metrics below require knowing whether the instance is clustered. Options
(general Db2 12.1 knowledge — verify):

| Probe | SQL | Meaning |
|---|---|---|
| Member topology | `SELECT COUNT(*) AS n_members, COUNT(DISTINCT MEMBER) FROM TABLE(MON_GET_INSTANCE(-2))` | >1 member ⇒ clustered (DPF or pureScale) |
| pureScale CF present | `SELECT COUNT(*) FROM TABLE(MON_GET_CF(-2))` (or `SYSIBMADM.DB2_CF`) | >0 rows ⇒ pureScale |
| Member vs CF roles | `SELECT ID, MEMBER_TYPE FROM SYSIBMADM.DB2_MEMBER` (`_raw/03-sysibmadm-objects.txt` L23) | `MEMBER_TYPE` ∈ {MEMBER, CF} distinguishes DB members from CF nodes |
| Edition probe | `SELECT * FROM TABLE(ENV_GET_INSTANCE_INFO())` / `SYSIBMADM.ENV_INST_INFO` (`_raw/03` L30) | `IS_PURESCALE`-style flag (verify exact column) |

**Recommended:** detect once per run (mirror the MySQL `GlobalVariables` cached-probe
pattern, `code-mysql-metrics.md` §8). Expose `is_purescale` / `is_dpf` capability gates.
Emit FCM-channel metrics when `is_dpf or is_purescale`; emit CF + GBP-structure metrics
only when `is_purescale`. Tag everything with `member` (and `cf_id` / `host_name` for CF
metrics). Wrap each query so a missing function / authority degrades gracefully (the
postgres/mysql degradation pattern, `code-postgres-metrics.md` §2, `code-mysql-metrics.md`
§11.4).

---

## 1. MASTER MAPPING TABLE

Legend: type = Datadog submit type (`monotonic_count` shown as MC, catalog `count`);
gauge=G; rate=R. Tags listed are *additional* to base instance tags
(`db`, `database_hostname`, `database_instance`, plus a `db2_version` tag mirroring
`postgresql_version`). "pg/mysql analog" column: `—` = no analog; `(weak)` = loose intent
match only. Version-gating in the Notes column.

### 1A. FCM — inter-member messaging (DPF + pureScale)

Source primary: **`MON_GET_FCM(member)`** (general Db2 12.1 — verify columns). Embedded
duplicate counters confirmed in `MON_GET_DATABASE`/`_CONNECTION`/`_SERVICE_SUBCLASS`/
`_WORKLOAD` (confirmed in `_raw/02`).

| pg/mysql analog | Db2 source: fn + exact column | proposed ibm_db2.<name> | type | unit | tags | notes / version-gating |
|---|---|---|---|---|---|---|
| — (mysql Galera `wsrep_replicated_bytes` is a *weak* analog) | `MON_GET_FCM` / `MON_GET_DATABASE`.`FCM_SEND_VOLUME` (confirmed `_raw/02` L70,1080,1722,2106) | `ibm_db2.fcm.send_volume` | MC | byte | member | DPF+pureScale. bytes sent over FCM since activation |
| — | `...FCM_RECV_VOLUME` (confirmed `_raw/02`) | `ibm_db2.fcm.recv_volume` | MC | byte | member | DPF+pureScale |
| — | `...FCM_SENDS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.sends` | MC | message | member | DPF+pureScale |
| — | `...FCM_RECVS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.recvs` | MC | message | member | DPF+pureScale |
| postgres `replication.wal_*_lag` (weak — both = inter-node wait) | `...FCM_SEND_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.fcm.send_wait_time` | MC | millisecond | member | time agents spent blocked sending FCM. High = network/peer pressure |
| postgres `replication.wal_*_lag` (weak) | `...FCM_RECV_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.fcm.recv_wait_time` | MC | millisecond | member | time agents spent blocked receiving FCM |
| — | `...FCM_SEND_WAITS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.send_waits` | MC | wait | member | count of send blocks; pair with send_wait_time for avg |
| — | `...FCM_RECV_WAITS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.recv_waits` | MC | wait | member | count of recv blocks |
| — | `...FCM_MESSAGE_SEND_VOLUME` (confirmed `_raw/02`) | `ibm_db2.fcm.message.send_volume` | MC | byte | member | control-message subchannel (vs TQ data) |
| — | `...FCM_MESSAGE_RECV_VOLUME` (confirmed `_raw/02`) | `ibm_db2.fcm.message.recv_volume` | MC | byte | member | |
| — | `...FCM_MESSAGE_SENDS_TOTAL` / `_RECVS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.message.sends` / `.recvs` | MC | message | member | |
| — | `...FCM_MESSAGE_SEND_WAIT_TIME` / `_RECV_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.fcm.message.send_wait_time` / `.recv_wait_time` | MC | millisecond | member | |
| — | `...FCM_MESSAGE_SEND_WAITS_TOTAL` / `_RECV_WAITS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.message.send_waits` / `.recv_waits` | MC | wait | member | |
| — (mysql Galera `wsrep_received_bytes` weak) | `...FCM_TQ_SEND_VOLUME` (confirmed `_raw/02` L192,1201,1842,2224) | `ibm_db2.fcm.tq.send_volume` | MC | byte | member | **table-queue** subchannel = MPP data shuffle for parallel query (DPF). Highest-signal for query-parallelism cost |
| — | `...FCM_TQ_RECV_VOLUME` (confirmed `_raw/02`) | `ibm_db2.fcm.tq.recv_volume` | MC | byte | member | |
| — | `...FCM_TQ_SENDS_TOTAL` / `_RECVS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.tq.sends` / `.recvs` | MC | message | member | |
| — | `...FCM_TQ_SEND_WAIT_TIME` / `_RECV_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.fcm.tq.send_wait_time` / `.recv_wait_time` | MC | millisecond | member | TQ flow-control stalls = parallel-query skew/contention |
| — | `...FCM_TQ_SEND_WAITS_TOTAL` / `_RECV_WAITS_TOTAL` (confirmed `_raw/02`) | `ibm_db2.fcm.tq.send_waits` / `.recv_waits` | MC | wait | member | |

**FCM resource gauges** (from `MON_GET_FCM`, general Db2 12.1 — verify; classic
`fcm_num_buffers`/`fcm_num_channels` engine counters):

| pg/mysql analog | Db2 source: fn + column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| — | `MON_GET_FCM`.`BUFF_FREE` (verify) | `ibm_db2.fcm.buffers.free` | G | buffer | member | free FCM buffers now |
| — (postgres conn `percent_usage` weak) | `MON_GET_FCM`.`BUFF_FREE_BOTTOM` (verify) | `ibm_db2.fcm.buffers.free_low_water` | G | buffer | member | low-water free buffers ⇒ FCM buffer starvation if →0; tune `fcm_num_buffers` |
| — | `MON_GET_FCM`.`BUFF_TOTAL` (verify) | `ibm_db2.fcm.buffers.total` | G | buffer | member | configured FCM buffers (= `fcm_num_buffers`) |
| — | `MON_GET_FCM`.`CH_FREE` (verify) | `ibm_db2.fcm.channels.free` | G | channel | member | free FCM channels now |
| — | `MON_GET_FCM`.`CH_FREE_BOTTOM` (verify) | `ibm_db2.fcm.channels.free_low_water` | G | channel | member | low-water free channels ⇒ channel exhaustion |
| — | `MON_GET_FCM`.`CH_TOTAL` (verify) | `ibm_db2.fcm.channels.total` | G | channel | member | configured channels |

> Derived ratio worth computing (mirrors postgres `percent_usage_connections`,
> `code-postgres-metrics.md` §4.4): `ibm_db2.fcm.buffers.utilized` =
> `(BUFF_TOTAL-BUFF_FREE)/BUFF_TOTAL*100` (gauge, percent) and same for channels — these are
> the actionable "near exhaustion" signals.

### 1B. FCM_CONNECTION_LIST — per-member-pair channel detail

Source: **`MON_GET_FCM_CONNECTION_LIST(member)`** (general Db2 12.1 — verify; confirmed
present `_raw/01` L31). One row per (source member, target member) channel. Higher
cardinality — gate behind a config flag.

| pg/mysql analog | Db2 source | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| — | `MON_GET_FCM_CONNECTION_LIST`.`TOTAL_BYTES_SENT` (verify) | `ibm_db2.fcm.connection.bytes_sent` | MC | byte | member, remote_member | per member-pair link volume |
| — | `...TOTAL_BYTES_RECEIVED` (verify) | `ibm_db2.fcm.connection.bytes_received` | MC | byte | member, remote_member | |
| postgres `wal_receiver.connected` (weak) | `...CONNECTION_STATUS` (verify) | `ibm_db2.fcm.connection.status` | G | — | member, remote_member, status | categorical → emit 1 with `status:` tag |
| — | `...BUFFERS_SENT` / `BUFFERS_RECEIVED` (verify) | `ibm_db2.fcm.connection.buffers_sent` / `.buffers_received` | MC | buffer | member, remote_member | |

> Cardinality = members². On a 4-member pureScale = 12 series/metric; manageable. Gate
> behind `collect_fcm_connection_metrics` (default False) mirroring postgres `relations`
> opt-in (`code-postgres-metrics.md` §6).

### 1C. CF wait time embedded in request-time functions (confirmed)

Source: `CF_WAIT_TIME` + `CF_WAITS` columns confirmed in `MON_GET_DATABASE` (region),
`MON_GET_CONNECTION`, `MON_GET_SERVICE_SUBCLASS`, `MON_GET_WORKLOAD` (confirmed `_raw/02`
L162,1169,1812,2194 for `CF_WAIT_TIME`). These are part of the `TOTAL_WAIT_TIME`
decomposition (`db2-monget-catalog-2.md` L236 lists `CF_WAIT_TIME` among
SERVICE_SUBCLASS wait components).

| pg/mysql analog | Db2 source: fn + column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| postgres `replication.*_lag` / mysql Galera `wsrep_flow_control_paused_ns` (weak — both = cluster-sync wait) | `MON_GET_DATABASE`.`CF_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.cf.wait_time` | MC | millisecond | db, member | total time agents waited on CF requests. **The single highest-value pureScale health metric** — rising = CF/interconnect bottleneck |
| — | `MON_GET_DATABASE`.`CF_WAITS` (confirmed `_raw/02`) | `ibm_db2.cf.waits` | MC | wait | db, member | count of CF waits; pair for avg CF wait |
| — | `MON_GET_SERVICE_SUBCLASS`.`CF_WAIT_TIME` / `CF_WAITS` (confirmed `_raw/02`) | (same names, tagged by class) | MC | millisecond / wait | service_superclass, service_subclass, member | per-WLM-class CF wait attribution (only if SUBCLASS collection enabled) |
| — | `MON_GET_WORKLOAD`.`CF_WAIT_TIME` / `CF_WAITS` (confirmed `_raw/02`) | (same names, tagged by workload) | MC | millisecond / wait | workload_name, member | per-workload CF wait attribution |

> Recommendation: collect `cf.wait_time`/`cf.waits` at the **database** scope
> unconditionally on pureScale (cheap, single row/member). Class/workload-scoped CF waits
> only if the WLM-class collectors are already enabled (avoid duplicate queries).

### 1D. MON_GET_CF — CF structure resources & status

Source: **`MON_GET_CF(cf_id)`** (general Db2 12.1 — verify; confirmed present `_raw/01`
L20). One row per CF (primary + secondary). Also `SYSIBMADM.DB2_CF` view (`_raw/03` L20)
and `SYSIBMADM.ENV_CF_SYS_RESOURCES` (`_raw/03` L28) for host-level CF resource info.

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| postgres `replication.*` role / mysql `replication.group.member_status` (weak) | `MON_GET_CF`.`STATE` (verify) | `ibm_db2.cf.state` | G | — | cf_id, host_name, state | categorical CF state (PRIMARY/PEER/CATCHUP/...) → emit 1 with `state:` tag; service-check candidate |
| mysql Galera `wsrep_cluster_size` (weak) | `MON_GET_CF` row count / `DB2_CF` | `ibm_db2.cf.count` | G | node | — | # CFs reporting (expect 2: primary+secondary) |
| postgres `database_size` (weak — capacity) | `MON_GET_CF`.`CURRENT_CF_GBP_SIZE` (verify) | `ibm_db2.cf.gbp.size` | G | page | cf_id | configured GBP structure size in CF |
| — | `MON_GET_CF`.`CURRENT_CF_LOCK_SIZE` (verify) | `ibm_db2.cf.lock.size` | G | page | cf_id | global lock manager (GLM) structure size |
| — | `MON_GET_CF`.`CURRENT_CF_SCA_SIZE` (verify) | `ibm_db2.cf.sca.size` | G | page | cf_id | shared communication area structure size |
| postgres `percent_usage_connections` (weak — saturation) | `MON_GET_CF`.`CURRENT_CF_MEM_SIZE` / `TARGET_CF_MEM_SIZE` (verify) | `ibm_db2.cf.memory.current` / `.target` | G | page | cf_id | CF self-tuning memory; current vs target |
| — | `ENV_CF_SYS_RESOURCES`.`MEMORY_TOTAL` / `MEMORY_FREE` (verify, `_raw/03` L28) | `ibm_db2.cf.host.memory_total` / `.memory_free` | G | byte | cf_id, host_name | CF host OS memory |

### 1E. MON_GET_CF_CMD — CF command latency by request type

Source: **`MON_GET_CF_CMD(cf_id)`** (general Db2 12.1 — verify; confirmed `_raw/01` L21).
One row per (CF, command-type). The CF-side analog of "what requests are slow."

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| postgres `blk_read_time` (weak — per-op latency) | `MON_GET_CF_CMD`.`TOTAL_CF_REQUESTS` (verify) | `ibm_db2.cf.cmd.requests` | MC | request | cf_id, cf_cmd_name | requests of this command type to the CF |
| postgres `blk_read_time` (weak) | `MON_GET_CF_CMD`.`TOTAL_CF_CMD_TIME_MICRO` (verify; **microseconds**) | `ibm_db2.cf.cmd.time` | MC | microsecond | cf_id, cf_cmd_name | total CF-side service time for this command. NOTE unit is µs not ms — verify and set per_unit accordingly |
| — | derived `time/requests` | `ibm_db2.cf.cmd.avg_time` | G | microsecond | cf_id, cf_cmd_name | per-command avg latency; key CF-tuning signal |

### 1F. MON_GET_CF_WAIT_TIME — CF wait time by command (member-side)

Source: **`MON_GET_CF_WAIT_TIME(member)`** (general Db2 12.1 — verify; confirmed `_raw/01`
L22). Member-side view of time spent waiting on each CF command type (complements
1E which is CF-side service time).

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| — | `MON_GET_CF_WAIT_TIME`.`TOTAL_CF_WAIT_TIME_MICRO` (verify; **µs**) | `ibm_db2.cf.cmd.wait_time` | MC | microsecond | member, cf_id, cf_cmd_name | member-side wait per CF command type. Breaks down `ibm_db2.cf.wait_time` (1C) by command — high-signal for *which* CF op is slow |
| — | `MON_GET_CF_WAIT_TIME`.`TOTAL_CF_REQUESTS` (verify) | (reuse `ibm_db2.cf.cmd.requests` or add `.wait_requests`) | MC | request | member, cf_id, cf_cmd_name | |

### 1G. MON_GET_GROUP_BUFFERPOOL — GBP structure castout & cross-invalidation

Source: **`MON_GET_GROUP_BUFFERPOOL(member)`** (general Db2 12.1 — verify; confirmed
`_raw/01` L32). GBP-structure-level engine counters: castout (writing dirty pages from CF
GBP to disk) and cross-member page invalidation. **Distinct from** the per-bufferpool
`POOL_*_GBP_*` page-read counters that the bufferpool category owns (`map-bufferpool.md`
L69-70,161-163). The GBP hit-ratio gauges (`ibm_db2.bufferpool.group.*.hit_percent`)
already EXIST in metadata.csv (rows 13-17) — **do not redefine them here.**

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| postgres `bgwriter.buffers_checkpoint` (weak — async flush) | `MON_GET_GROUP_BUFFERPOOL`.`NUM_GBP_FULL` (verify) | `ibm_db2.gbp.full` | MC | event | member | # times the GBP filled (forced castout). Rising = GBP undersized |
| postgres `bgwriter.buffers_clean` (weak) | `...CASTOUT_PAGES` / `NUM_CASTOUTS` (verify) | `ibm_db2.gbp.castouts` | MC | page | member | dirty pages cast out from GBP to disk |
| mysql Galera `wsrep_local_cert_failures` (weak — cross-node conflict) | `...CROSS_INVALIDATIONS` / `XI_PAGES` (verify) | `ibm_db2.gbp.cross_invalidations` | MC | page | member | pages invalidated in this member's LBP because another member updated them. **Core pureScale write-sharing cost signal** |
| — | `...GBP_L_READS` (structure-level; verify vs bufferpool) | `ibm_db2.gbp.reads.logical` | MC | page | member | GBP logical reads at structure scope (cross-check with bufferpool category — may be redundant; prefer bufferpool's per-BP version) |
| — | `...GBP_P_READS` (verify) | `ibm_db2.gbp.reads.physical` | MC | page | member | GBP misses → disk read |
| postgres `buffercache.dirty_buffers` (weak) | derived | `ibm_db2.gbp.directory.utilized` (if a directory-entries column exists, verify) | G | percent | member | GBP directory-entry pressure (sep. from data-area pressure) |

> **Overlap guard:** if the bufferpool collector already emits `POOL_*_GBP_L_READS`-derived
> metrics, do NOT also emit `ibm_db2.gbp.reads.*`. Keep this function for the
> *castout/invalidation* counters (`full`, `castouts`, `cross_invalidations`) which the
> bufferpool category does NOT cover. The bufferpool doc already proposes
> `ibm_db2.bufferpool.group.<x>.invalid_pages` from `POOL_*_GBP_INVALID_PAGES`
> (`map-bufferpool.md` L162) — that is the *per-bufferpool* invalidation; `gbp.cross_
> invalidations` here is the *GBP-structure* aggregate. Decide which granularity to keep to
> avoid double counting (recommend: keep per-BP `invalid_pages` for the bufferpool category,
> and `gbp.castouts` + `gbp.full` here).

### 1H. pureScale page-reclaim wait (shared-disk space contention) — confirmed columns

Source: `RECLAIM_WAIT_TIME` + `SPACEMAPPAGE_RECLAIM_WAIT_TIME` confirmed in DATABASE/
CONNECTION/SERVICE_SUBCLASS/WORKLOAD (`_raw/02` L159-160,1166-1167,1809-1810,2191-2192).
Part of `TOTAL_WAIT_TIME` (`db2-monget-catalog-2.md` L236). pureScale-specific: time spent
waiting to reclaim extents/space-map pages held by other members.

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| — | `MON_GET_DATABASE`.`RECLAIM_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.reclaim.wait_time` | MC | millisecond | db, member | pureScale extent-reclaim contention |
| — | `MON_GET_DATABASE`.`SPACEMAPPAGE_RECLAIM_WAIT_TIME` (confirmed `_raw/02`) | `ibm_db2.reclaim.spacemap_wait_time` | MC | millisecond | db, member | space-map-page reclaim contention (insert-heavy pureScale) |

### 1I. Global lock contention (pureScale GLM) — confirmed columns

Source: `LOCK_WAIT_TIME_GLOBAL`, `LOCK_WAITS_GLOBAL`, `LOCK_ESCALS_GLOBAL`,
`LOCK_TIMEOUTS_GLOBAL` confirmed in `_raw/02` (DATABASE region). These are the
pureScale Global Lock Manager (CF-hosted GLM) counterparts of the local lock counters the
**locking-concurrency** category owns. Flag to that category for ownership; listed here
because they are pureScale-only and CF-mediated.

| pg/mysql analog | Db2 source: column | proposed ibm_db2.<name> | type | unit | tags | notes |
|---|---|---|---|---|---|---|
| postgres `locks.*` / mysql `Innodb_row_lock_time` (weak) | `MON_GET_DATABASE`.`LOCK_WAIT_TIME_GLOBAL` (confirmed `_raw/02`) | `ibm_db2.lock.wait_time_global` | MC | millisecond | db, member | time waiting on globally-managed (CF) locks. **Owned by locking-concurrency category — cross-ref only** |
| — | `LOCK_WAITS_GLOBAL` (confirmed `_raw/02`) | `ibm_db2.lock.waits_global` | MC | lock | db, member | (locking category) |
| — | `LOCK_ESCALS_GLOBAL` (confirmed `_raw/02`) | `ibm_db2.lock.escals_global` | MC | lock | db, member | (locking category) |
| — | `LOCK_TIMEOUTS_GLOBAL` (confirmed `_raw/02`) | `ibm_db2.lock.timeouts_global` | MC | lock | db, member | (locking category) |

---

## 2. Db2-native metrics worth adding with NO pg/mysql analog

These have no Postgres or MySQL counterpart and are pure pureScale/DPF value-adds. Ranked
by signal value for the implementer:

1. **`ibm_db2.cf.wait_time` / `ibm_db2.cf.waits`** (1C) — the single best pureScale health
   KPI. Cheap (one row per member from `MON_GET_DATABASE`), no analog, directly answers "is
   the CF/interconnect the bottleneck."
2. **`ibm_db2.gbp.cross_invalidations`** (1G) — measures the fundamental cost of write
   sharing across members; no shared-disk-cluster analog exists in pg/mysql.
3. **`ibm_db2.fcm.tq.*` (table-queue volume/wait)** (1A) — MPP parallel-query data-shuffle
   cost; unique to DPF.
4. **`ibm_db2.fcm.buffers.free_low_water` / `ibm_db2.fcm.channels.free_low_water`** (1A) —
   FCM resource-exhaustion early warning; tune `fcm_num_buffers`/`fcm_num_channels`.
5. **`ibm_db2.gbp.castouts` / `ibm_db2.gbp.full`** (1G) — GBP sizing/pressure.
6. **`ibm_db2.cf.cmd.avg_time` per `cf_cmd_name`** (1E/1F) — pinpoints WHICH CF operation
   is slow (lock vs GBP read vs SCA).
7. **`ibm_db2.reclaim.wait_time` / `.spacemap_wait_time`** (1H) — pureScale shared-disk
   space contention on insert-heavy workloads.
8. **`ibm_db2.cf.state` / `ibm_db2.cf.count`** (1D) — CF availability; pairs with a CF
   service check.

---

## 3. pg/mysql metrics with NO Db2 equivalent in this category (flag for plan)

These cluster/replication metrics exist in pg/mysql but have **no pureScale/FCM analog**
because pureScale is shared-disk (single copy of data) rather than shared-nothing
replicated:

| pg/mysql metric | why no Db2 fcm-purescale equivalent |
|---|---|
| `postgresql.replication_delay` / `_delay_bytes`, `postgresql.replication.wal_*_lag`, `sent/write/flush/replay_lsn_delay` | These measure **log-shipping lag to a replica**. pureScale has no log replay between members (shared disk, single data copy). The Db2 analog of *replication lag* is **HADR** (`MON_GET_HADR`, see `map-hadr-replication.md`) — a separate category, NOT pureScale. |
| `postgresql.replication_slot.*` (spill/stream/xmin) | Logical-decoding/slot concept; no Db2 equivalent. |
| `postgresql.wal_receiver.*`, subscription metrics | Streaming/logical replication; HADR-adjacent, not pureScale. |
| `mysql.galera.wsrep_cluster_size`, `wsrep_local_state`, `wsrep_received_bytes`, `wsrep_flow_control_*` | Galera = **shared-nothing write-set replication**. Weak intent overlap with `cf.count` / `cf.state` / `fcm.*_volume` / `cf.wait_time` but NOT a true mapping: Galera replicates write-sets between full copies; pureScale shares one disk via the CF. Mapped as `(weak)` above where intent loosely aligns; do not present as equivalents. |
| `mysql.replication.group.*` (group replication transactions/conflicts) | Same as Galera — shared-nothing consensus replication; no pureScale equivalent. The nearest Db2 conflict signal is `gbp.cross_invalidations`, but the mechanism differs fundamentally. |
| `postgresql.bgwriter.*` (checkpoint/buffers) | Single-node page cleaning. The pureScale castout engine (`gbp.castouts`) is the *cluster* analog but operates at the CF/GBP layer, not a local bgwriter; loose mapping only. |

---

## 4. Implementation notes (synthesis for the plan agent)

1. **Gate the whole category** behind a cached pureScale/DPF probe (§0). Emit nothing on a
   non-clustered instance (the live 12.1.4 single-node container — so these will be
   `# no cov` in unit tests exactly like the existing `group.*` paths, `map-bufferpool.md`
   L169). Provide a pureScale fixture or mock for test coverage.
2. **Use the new QueryExecutor `columns` dict style** (Paradigm B,
   `code-mysql-metrics.md` §0/§5, `code-postgres-metrics.md` §1B) for every query here. Each
   `MON_GET_FCM`/`MON_GET_CF*`/`MON_GET_GROUP_BUFFERPOOL` call is one declarative dict with
   metric + tag columns.
3. **Pass member = -2** (all members) to fan out per-member, then tag with `MEMBER`
   (mirrors postgres per-db row fan-out, `code-postgres-metrics.md` §5). For CF functions,
   pass the CF id arg as `-2` (all CFs) and tag with `cf_id`/`host_name`.
4. **Two-tier collection:** (a) cheap always-on (on pureScale) = `cf.wait_time`,
   `cf.waits`, `reclaim.*`, FCM volume/wait from `MON_GET_DATABASE` (already one row/member,
   reuse the DATABASE query you build for the instance-database category — do NOT issue a
   separate query just for these embedded columns); (b) opt-in heavier = `MON_GET_FCM`
   resource gauges, `MON_GET_CF*` detail, `MON_GET_GROUP_BUFFERPOOL`,
   `MON_GET_FCM_CONNECTION_LIST` behind config flags (`collect_fcm_metrics`,
   `collect_cf_metrics`, `collect_fcm_connection_metrics`; default False, mirror
   `extra_status_metrics`/`relations` opt-ins).
5. **CF command time units:** `MON_GET_CF_CMD`/`MON_GET_CF_WAIT_TIME` totals are commonly in
   **microseconds** (unlike the ms `*_WAIT_TIME` in request functions). VERIFY exact units
   from a live DESCRIBE/IBM docs before setting `unit_name`/`per_unit_name` in metadata.csv.
6. **Avoid double-mapping GBP** with the bufferpool category (§1G overlap guard). Owner
   split: bufferpool = per-BP `POOL_*_GBP_*` reads + hit ratios + `invalid_pages`;
   fcm-purescale = GBP-structure castout/full/cross-invalidation. Global lock `*_GLOBAL`
   columns (§1I) belong to locking-concurrency — cross-reference only.
7. **Three functions need a live DESCRIBE before coding** (single-node container will still
   return schema even with empty rows): capture
   `DESCRIBE SELECT * FROM TABLE(MON_GET_FCM(-2))`,
   `DESCRIBE SELECT * FROM TABLE(MON_GET_CF(-2))`,
   `DESCRIBE SELECT * FROM TABLE(MON_GET_GROUP_BUFFERPOOL(-2))` (and `_CF_CMD`,
   `_CF_WAIT_TIME`, `_FCM_CONNECTION_LIST`) to lock exact column names/types. Everything in
   §1A resource gauges, §1D-§1G is marked **(verify)** for this reason; §1A volume/wait
   counters, §1C, §1H, §1I are **confirmed** via the embedded copies in `_raw/02`.
8. **metadata.csv:** add every emitted metric with `integration=ibm_db2`, correct
   `metric_type` (catalog vocab: monotonic→`count`, gauge→`gauge`), `unit_name`/
   `per_unit_name` (byte/millisecond/microsecond/page/buffer/channel/message/wait/request),
   `orientation` (wait/contention metrics = -1; volume/throughput = 0; free-resource gauges
   = 1), and a description naming the enabling config flag + tags + the pureScale-only
   caveat. The current file has 49 metrics (rows 2-50); none are FCM/CF/GBP-structure.
9. **Tags taxonomy for this category:** `member` (always, on every metric), `cf_id` +
   `host_name` (CF metrics), `cf_cmd_name` (CF command metrics), `remote_member` (FCM
   connection list), plus base `db`/`database_hostname`/`database_instance`/`db2_version`.
10. **Service check** opportunity: `ibm_db2.cf.status` from `MON_GET_CF.STATE` /
    `SYSIBMADM.DB2_CF` (PRIMARY+PEER = OK; CATCHUP/error = WARN/CRIT) — pairs with the
    `cf.state` gauge. Out of scope for "metrics" but flag for the plan.

---

## 5. Quick reference — confirmed vs. needs-verify

**Empirically confirmed in `_raw/02-monget-key-columns.txt`** (BIGINT counters, embedded in
DATABASE/CONNECTION/SERVICE_SUBCLASS/WORKLOAD):
`FCM_SEND_VOLUME`, `FCM_RECV_VOLUME`, `FCM_SENDS_TOTAL`, `FCM_RECVS_TOTAL`,
`FCM_SEND_WAIT_TIME`, `FCM_RECV_WAIT_TIME`, `FCM_SEND_WAITS_TOTAL`, `FCM_RECV_WAITS_TOTAL`,
`FCM_MESSAGE_{SEND,RECV}_VOLUME`, `FCM_MESSAGE_{SENDS,RECVS}_TOTAL`,
`FCM_MESSAGE_{SEND,RECV}_WAIT_TIME`, `FCM_MESSAGE_{SEND,RECV}_WAITS_TOTAL`,
`FCM_TQ_{SEND,RECV}_VOLUME`, `FCM_TQ_{SENDS,RECVS}_TOTAL`,
`FCM_TQ_{SEND,RECV}_WAIT_TIME`, `FCM_TQ_{SEND,RECV}_WAITS_TOTAL`,
`CF_WAIT_TIME`, `CF_WAITS`, `RECLAIM_WAIT_TIME`, `SPACEMAPPAGE_RECLAIM_WAIT_TIME`,
`LOCK_WAIT_TIME_GLOBAL`, `LOCK_WAITS_GLOBAL`, `LOCK_ESCALS_GLOBAL`, `LOCK_TIMEOUTS_GLOBAL`.

**Functions confirmed PRESENT but NOT DESCRIBE'd (columns = general Db2 12.1 knowledge,
verify):** `MON_GET_FCM` (`_raw/01` L30), `MON_GET_FCM_CONNECTION_LIST` (L31),
`MON_GET_CF` (L20), `MON_GET_CF_CMD` (L21), `MON_GET_CF_WAIT_TIME` (L22),
`MON_GET_GROUP_BUFFERPOOL` (L32). Plus SYSIBMADM views `DB2_CF`, `DB2_MEMBER`,
`ENV_CF_SYS_RESOURCES`, `DB2_CLUSTER_HOST_STATE`, `SNAPFCM`, `SNAPFCM_PART`
(`_raw/03` L20,23,28,21,68,69 — prefer MON_GET_* over the deprecated SNAP* views).
