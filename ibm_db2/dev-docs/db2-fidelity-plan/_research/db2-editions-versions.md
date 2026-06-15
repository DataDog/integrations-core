# Db2 EDITIONS & VERSIONS — Feature-Availability Matrix and Version/Edition Gating

Raw research input for the Db2 DBM implementation plan. This doc answers: **which monitoring
features (MON_GET functions, SYSIBMADM views, EXPLAIN, config reads) are available on which Db2
edition/version/topology, and how the agent should detect & guard them in SQL.**

> **TARGET PLATFORM — stated clearly up front: this integration targets Db2 LUW
> (Linux/UNIX/Windows).** The live ground-truth server is **`DB2/LINUXX8664 12.1.4.0`**, Db2
> **Community Edition** (`INSTALLED_PROD='DEC'`, `LICENSE_TYPE='COMMUNITY'`), single-member,
> non-DPF, non-pureScale, non-HADR
> (`_raw/01-version-and-monget-functions.txt:4`, `db2-config-settings.md:236-254`).
> Db2 on Cloud, Db2 Warehouse / Integrated Analytics, and **Db2 for z/OS** are explicitly
> **out of scope** (their monitoring SQL surface differs — see §7). Where a claim could not be
> confirmed against the live container it is marked **"(general Db2 12.1 knowledge — verify)"**.

> Sibling docs (read for the per-feature column detail): `db2-live-pkgcache.md` (query metrics /
> `MON_GET_PKG_CACHE_STMT`), `db2-live-activity.md` (samples / `MON_CURRENT_SQL` etc.),
> `db2-config-settings.md` (settings / version+edition detection SQL — the canonical source for
> §3 below; this doc extends it with the **feature-gating** angle).

---

## 0. TL;DR (load-bearing facts)

1. **Detect version with a packed integer**, not string parsing:
   `SELECT versionnumber FROM SYSIBM.SYSVERSIONS` → `12010400` (= `VV RR MM FF` =
   `12.01.04.00`). Trivially `>=` / `<` comparable. Live value `12010400`
   (`db2-config-settings.md:351`). Fall back to `ENV_INST_INFO.SERVICE_LEVEL` (`DB2 v12.1.4.0`)
   or the driver `ibm_db.get_db_info(conn, ibm_db.SQL_DBMS_VER)` already used by the check
   (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28`).
2. **Detect edition** with:
   `SELECT installed_prod, license_type FROM SYSIBMADM.ENV_PROD_INFO WHERE license_installed='Y'`.
   Live → `DEC` / `COMMUNITY` (`db2-config-settings.md:254-259`). The product *code* (DEC, ESE,
   AESE, AWSE, WSE, …) is the edition discriminator.
3. **Detect topology (the real gate for cluster-only features)** — edition alone does NOT tell you
   if pureScale/DPF/HADR features will return rows:
   - DPF/partitionable: `ENV_INST_INFO.IS_INST_PARTITIONABLE` (live `0`),
     `NUM_DBPARTITIONS` (live `1`), `NUM_MEMBERS` (live `1`)
     (`db2-config-settings.md:236-239`).
   - pureScale: presence of CF members in `SYSIBMADM.DB2_CF` / `MON_GET_CF` returning rows; on a
     non-pureScale instance these functions exist but return **0 rows**.
   - HADR: `MON_GET_HADR` returns **0 rows** when HADR is not configured (the function exists in
     all LUW editions).
4. **The core gating principle for THIS integration: the function/view almost always EXISTS on
   LUW 12.1 regardless of edition; what changes is whether it returns ROWS and whether specific
   COLUMNS exist.** So the agent should prefer **runtime introspection + empty-result tolerance**
   over hard version/edition branching. This is exactly what the existing check already does for
   pureScale GBP metrics — it computes the group-buffer-pool ratio only when the `*_gbp_*` reads
   are non-zero (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:232-235,
   269-272, 306-309, 343-346, 365-377`), never branching on edition.
5. **Column sets grow across fix packs / versions; column *layouts* of the config views are
   stable.** `MON_GET_PKG_CACHE_STMT` = **327 cols** on 12.1.4 (`db2-live-pkgcache.md:51,210`);
   `MON_GET_ACTIVITY` = **418 cols** (`db2-live-activity.md:84,356`). 11.5 has fewer of both.
   **Introspect columns at runtime** (DESCRIBE / `WHERE 1=0` probe + intersect with desired set);
   never hard-code a column list by fix pack (`db2-live-pkgcache.md:381-390`).
6. **Community Edition (`DEC`) does NOT restrict the monitoring SQL surface** in any way observed
   live: all 64 MON_GET functions in `_raw/01` are present, all 79 SYSIBMADM views in `_raw/03`
   are present, EXPLAIN works (`_raw/05`), package cache + activity + config reads all work
   (sibling docs). Community Edition limits are about **capacity** (cores/RAM), not feature
   *availability* (§4). So a customer on Community Edition gets the full DBM feature set the same
   as ESE — the only edition-specific gap is genuinely cluster-only telemetry (CF/GBP/FCM) which
   requires the pureScale topology that Community Edition can't run anyway.
7. **EXPLAIN works on the live community server** (`_raw/05-explain-test.txt:9-13`) and
   `EXPLAIN_OPERATOR` has the full cost schema — so plan capture is available on LUW Community.

---

## 1. Version landscape (what "12.1" vs "11.5" means and why it matters)

### 1.1 Supported / relevant LUW versions

| Version | Status (as of 2026) | Notes for monitoring |
|---|---|---|
| **11.5** ("Cancun"/Mod packs) | Widely deployed; long-term support | Baseline for the *existing* IBM docs the check links to are 11.1; semantics of MON_GET table functions are stable 11.5→12.1, but **column sets are smaller** (no `MODEL_PROVIDER_*`, fewer `*_CACHING_TIER_*`, fewer columnar `POOL_COL_*` variants). (general Db2 12.1 knowledge — verify) |
| **12.1** | Current; live server is **12.1.4.0** | All 64 MON_GET functions in `_raw/01`. New: `MODEL_PROVIDER_WAIT_TIME`/`MODEL_PROVIDER_WAITS_TOTAL` in pkg cache (AI/ML model-inference telemetry), expanded caching-tier + columnar columns (`db2-live-pkgcache.md:279,327`). |
| 11.1 | EOL / legacy | The current check's doc URLs point here (`SSEPGG_11.1.0`, `queries.py:5-15`). Treat as the floor the existing system metrics target. |
| 10.5 and earlier | EOL | Out of scope. |

**Packed version numbers** (for `WHERE versionnumber >= N` gating):
- 11.1.0.0 → `11010000`
- 11.5.0.0 → `11050000`
- 12.1.0.0 → `12010000`
- 12.1.4.0 → `12010400` (live, `db2-config-settings.md:351`)

### 1.2 11.5 vs 12.1 monitoring differences (concrete)

| Area | 11.5 | 12.1 | Gate / handling |
|---|---|---|---|
| MON_GET function *set* | All core functions present (PKG_CACHE_STMT, ACTIVITY, CONNECTION, UNIT_OF_WORK, DATABASE, BUFFERPOOL, TABLESPACE, TRANSACTION_LOG, INSTANCE, HADR, CF, GROUP_BUFFERPOOL, FCM, …) | Same set + nothing removed; the 64 in `_raw/01` are the 12.1.4 list | Introspect: `SELECT 1 FROM SYSCAT.ROUTINES WHERE routineschema='SYSPROC' AND routinename=:fn` before calling a rarely-present fn |
| `MON_GET_PKG_CACHE_STMT` columns | fewer than 327 | **327** (`db2-live-pkgcache.md:51`) | Runtime column introspection (§5) |
| `MON_GET_ACTIVITY` columns | fewer than 418 | **418** (`db2-live-activity.md:84`) | Runtime column introspection (§5) |
| New 12.1 columns | absent | `MODEL_PROVIDER_WAIT_TIME`, `MODEL_PROVIDER_WAITS_TOTAL`, expanded `POOL_*_CACHING_TIER_*`, `POOL_COL_*`, columnar/synopsis families (`db2-live-pkgcache.md:275-327`) | Defensive `SELECT` — only request columns present in `cursor.description` |
| `ENV_SYS_INFO` columns | first 7 only | + `OS_FULL_VERSION`, `OS_KERNEL_VERSION`, `OS_ARCH_TYPE` (`db2-config-settings.md:278-280`) | `SELECT *` and tolerate missing keys |
| `ENV_PROD_INFO` product codes | smaller list | adds AI editions `ADV_AI`, `STD_AI` (`db2-config-settings.md:246`) | Filter by `LICENSE_INSTALLED='Y'`, never enumerate codes |
| Config view layout (DBCFG/DBMCFG/REG_VARIABLES) | same shape | same shape; only **row count** grows (`db2-config-settings.md:388-394`) | Select all rows; don't hard-code parameter names |
| db2mon / monitor element semantics | stable | stable | Same gating on `mon_*_metrics` (§6) |

**Bottom line:** there is **no 11.5→12.1 difference that removes a feature** for this integration.
The differences are all *additive columns*. Runtime column introspection (§5) handles all of them;
explicit `versionnumber` branching is only needed if the plan wants to emit a 12.1-only metric
(e.g. model-provider wait time) and label it as such.

---

## 2. Edition landscape (LUW)

Db2 LUW ships in several editions. The product code lives in
`SYSIBMADM.ENV_PROD_INFO.INSTALLED_PROD` (the row where `LICENSE_INSTALLED='Y'`).

| Code | Edition | Capacity limits (typical) | Cluster features | Notes |
|---|---|---|---|---|
| **DEC** | **Db2 Community Edition** (live server) | **up to 4 cores / 16 GB RAM**, single instance (general Db2 12.1 knowledge — verify) | **No** pureScale, **no** DPF/MPP | Free; replaces old "Express-C". Full SQL/feature surface for monitoring. License `COMMUNITY` (`db2-config-settings.md:254`). |
| WSE | Workgroup Server Edition | mid-tier core/RAM cap | No pureScale | (general Db2 12.1 knowledge — verify) |
| AWSE | Advanced Workgroup Server Edition | mid-tier | pureScale-capable (limited) | (general — verify) |
| ESE | Enterprise Server Edition | no built-in cap | DPF add-on; pureScale add-on | The classic full server edition |
| AESE | Advanced Enterprise Server Edition | no cap | pureScale + DPF + BLU + compression all included | (general — verify) |
| ADV / ADV_AI / STD / STD_AI | newer "Advanced"/"Standard" (and AI) license bundles | varies | varies | 12.1 added the `*_AI` bundles (`db2-config-settings.md:246`) |
| STARTER / LITE / BASE | trial / lightweight | small | No | (general — verify) |

### 2.1 What edition actually gates

Edition gates two orthogonal things, **neither of which removes a monitoring function/view**:

1. **Capacity** (cores, RAM, DB size) — affects *how much* workload there is to monitor, not what
   you can query. Community Edition's 4-core/16 GB cap is a deployment constraint, not a
   monitoring-API constraint.
2. **Whether a *topology feature* can be enabled at all** — pureScale and DPF require an edition
   that licenses them (ESE+add-on / AESE / AWSE). Community Edition **cannot run pureScale or
   DPF**, so the CF/GBP/FCM functions, while *present*, will always return 0 rows on Community.

The monitoring SQL surface itself (MON_GET_*, SYSIBMADM, EXPLAIN, config views) is **edition-
independent on LUW** — confirmed live: the community container exposes the complete set
(`_raw/01`, `_raw/03`, `_raw/05`, sibling docs). So **the agent should not branch on edition to
decide whether a MON_GET function is callable.** Edition detection is useful only for:
- tagging telemetry (`db2_edition:community`),
- explaining empty cluster results,
- a possible "you're on Community, capacity-limited" advisory.

---

## 3. How to detect version / edition / topology in SQL (gating inputs)

(Canonical detail + live values in `db2-config-settings.md` §6; condensed here for gating.)

### 3.1 Version — packed integer (preferred for comparisons)
```sql
SELECT versionnumber, version_timestamp FROM SYSIBM.SYSVERSIONS;
-- live: 12010400, 2026-06-13-01.01.22   (db2-config-settings.md:351)
```
`versionnumber` = `VVRRMMFF`. Gate: `IF versionnumber >= 12010000 THEN <12.1-only feature>`.

### 3.2 Version — human string / build (rich)
```sql
SELECT service_level, bld_level, fixpack_num, release_num, num_members
FROM SYSIBMADM.ENV_INST_INFO;
-- live: 'DB2 v12.1.4.0', 's2602211313', 0, '02050110', 1   (db2-config-settings.md:236-239)
```
Table-function form (no view dep): `SELECT service_level, fixpack_num FROM TABLE(SYSPROC.ENV_GET_INST_INFO())`.

### 3.3 Edition / product / license
```sql
SELECT installed_prod, prod_release, license_type
FROM SYSIBMADM.ENV_PROD_INFO WHERE license_installed = 'Y';
-- live: 'DEC', '12.1', 'COMMUNITY'   (db2-config-settings.md:254-259)
```
`INSTALLED_PROD` = edition code (§2). `LICENSE_TYPE` distinguishes `COMMUNITY` vs licensed.

### 3.4 Topology — DPF / member count
```sql
SELECT is_inst_partitionable, num_dbpartitions, num_members FROM SYSIBMADM.ENV_INST_INFO;
-- live: 0, 1, 1  (single member, non-DPF)   (db2-config-settings.md:236-239)
```
- `IS_INST_PARTITIONABLE = 1` → DPF-capable; `NUM_DBPARTITIONS > 1` → actually partitioned.
- `NUM_MEMBERS > 1` with DB2_MEMBER rows of `MEMBER_TYPE='MEMBER'` + a CF → pureScale (§3.5).

### 3.5 Topology — pureScale (CF presence)
```sql
SELECT count(*) AS cf_count FROM SYSIBMADM.DB2_CF;            -- 0 on non-pureScale
-- or: SELECT count(*) FROM TABLE(MON_GET_CF(-2));            -- 0 rows on non-pureScale
SELECT id, member_type, state FROM SYSIBMADM.DB2_MEMBER;     -- shows MEMBER vs CF rows
```
`SYSIBMADM.DB2_CF` and `DB2_MEMBER` exist in `_raw/03-sysibmadm-objects.txt:21,23`. On the live
single-member community instance they will report a single member and no CF (general Db2 12.1
knowledge — verify the exact 0-row behavior; the views are present per `_raw/03`).

### 3.6 Topology — HADR (standby presence)
```sql
SELECT count(*) AS hadr_rows FROM TABLE(MON_GET_HADR(-1));   -- 0 rows when HADR not configured
```
`MON_GET_HADR` is in the 12.1.4 function list (`_raw/01:33`). Returns rows **only when the
database is in an HADR pair**. `SYSIBMADM.SNAPHADR` (`_raw/03:70`) is the legacy snapshot analog.

### 3.7 Driver-level fallback (no SQL, already in the check)
`ibm_db.get_db_info(conn, ibm_db.SQL_DBMS_VER)` → raw `MM.mm.uuuu`
(`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28`,
parsed at `ibm_db2.py:109-125`). Useful before a connection-scoped SQL probe is set up.

---

## 4. Db2 Community Edition (`DEC`) — what is and isn't limited

**Confirmed available on the live Community Edition 12.1.4.0 server** (so available to the DBM
feature set on Community):

| Capability | Evidence | Available on Community? |
|---|---|---|
| All 64 `MON_GET_*` table functions | `_raw/01-version-and-monget-functions.txt:11-74` | **YES** |
| All 79 `SYSIBMADM` views | `_raw/03-sysibmadm-objects.txt:9-86` | **YES** |
| Package-cache query metrics (`MON_GET_PKG_CACHE_STMT`, 327 cols) | `db2-live-pkgcache.md` (full live capture) | **YES** |
| Live activity / samples (`MON_CURRENT_SQL`, `MON_GET_ACTIVITY`) | `db2-live-activity.md` (full live capture) | **YES** |
| EXPLAIN + `EXPLAIN_OPERATOR` cost schema (plan capture) | `_raw/05-explain-test.txt:9-35` | **YES** |
| Config reads (DBCFG 194, DBMCFG 113, REG_VARIABLES 3) | `db2-config-settings.md:513-515` | **YES** |
| Monitor metrics collection settings (`mon_*_metrics`) | `_raw/04-monitor-config.txt` | **YES** |

**What Community Edition limits (capacity, NOT monitoring API):**
- Cores / RAM (≈4 cores / 16 GB) and a single instance. (general Db2 12.1 knowledge — verify)
- **Cannot enable pureScale or DPF** → CF/GBP/FCM telemetry will be empty (not a feature the agent
  can light up). This is the *only* edition-driven monitoring gap, and it is really a topology gap.
- No paid add-ons (BLU advisor, etc.) — irrelevant to the MON_GET-based DBM features.

**Implication for the plan:** treat Community Edition as a **full-feature target** for DBM (query
metrics, samples, settings, plans). Do not gate any feature off `LICENSE_TYPE='COMMUNITY'`. The
only edition-aware behavior worth adding is: when emitting CF/GBP/FCM/HADR metrics, skip silently
on empty results (which Community always produces).

---

## 5. Runtime COLUMN introspection (the primary "guard" mechanism)

Because column *sets* differ across versions/fixpacks but layouts don't, the agent must introspect
columns at runtime rather than version-branching. Pattern (mirrors Postgres `statements.py`,
`db2-live-pkgcache.md:381-390`):

1. Run a zero-row probe: `SELECT * FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1)) WHERE 1=0`
   (or `DESCRIBE SELECT ...`). The `ibm_db` cursor `description` lists available columns.
2. Intersect `available_columns` with the agent's `desired_columns`; build the SELECT from
   `sorted(available & desired)`.
3. Cache per (version, function) for the connection lifetime; re-probe on reconnect.

This single mechanism covers:
- 11.5 vs 12.1 additive columns (§1.2),
- fix-pack column additions within 12.1,
- the `MODEL_PROVIDER_*` / caching-tier / columnar families that may be absent on older builds.

**Function-existence introspection** (for rarely-present routines):
```sql
SELECT 1 FROM SYSCAT.ROUTINES
WHERE routineschema='SYSPROC' AND routinename='MON_GET_PKG_CACHE_STMT_DETAILS';
```
(Note: `MON_GET_PKG_CACHE_STMT_DETAILS` exists in `_raw/01:43` but was **not callable** by
`db2inst1` in the probe due to argument/grant issues — `db2-live-pkgcache.md:401-409`. Treat
`_DETAILS` variants as needing separate grant/signature verification; they are not required for
core features.)

---

## 6. Monitor-collection config gating (orthogonal to version/edition)

Timing/metric columns are populated only when the relevant `mon_*_metrics` DB CFG knob is at the
right level — this is **independent of version/edition** and must be checked at runtime via
`SYSIBMADM.DBCFG`. Live values (`_raw/04-monitor-config.txt:9-22`):

| Setting | Live value | Gates | Guard |
|---|---|---|---|
| `mon_act_metrics` | `BASE` | Activity timing cols (`TOTAL_ACT_TIME`, waits, `COORD_STMT_EXEC_TIME`, `WLM_QUEUE_TIME_TOTAL`) in `MON_GET_ACTIVITY` / pkg cache | emit timing-derived metrics only when `<> 'NONE'` (`db2-live-pkgcache.md:73-75`, `db2-live-activity.md:504-507`) |
| `mon_req_metrics` | `BASE` | Request-level timing | same |
| `mon_obj_metrics` | `EXTENDED` | Object (table/index/bufferpool) metrics | gate object metrics on `<> 'NONE'` |
| `mon_uow_data` / `mon_uow_pkglist` / `mon_uow_execlist` | `NONE`/`OFF`/`OFF` | UOW statement & package lists | not needed for core features |
| `mon_lck_msg_lvl` / `mon_lockwait` / `mon_locktimeout` / `mon_deadlock` | `1`/`NONE`/`NONE`/`WITHOUT_HIST` | lock-event monitor detail | gate lock-wait detail features |

Read them with:
```sql
SELECT name, value FROM SYSIBMADM.DBCFG
WHERE member = 0 AND name LIKE 'mon_%metrics' OR name IN ('mon_lockwait','mon_deadlock', ...);
```
All defaults on the live server are adequate for the timing columns; still introspect and degrade
gracefully if a customer set them to `NONE`.

---

## 7. LUW vs Db2-on-Cloud vs Warehouse vs z/OS (scope statement)

| Platform | In scope? | Monitoring SQL surface | Notes |
|---|---|---|---|
| **Db2 LUW** (Linux/UNIX/Windows) | **YES — this is the target** | Full MON_GET_* + SYSIBMADM as documented here; live server is LUW 12.1.4.0 | `_raw/01:4` server string `DB2/LINUXX8664 12.1.4.0` |
| **Db2 on Cloud** (managed LUW) | No (but mostly compatible) | Same MON_GET_*/SYSIBMADM engine (it *is* LUW under the hood), but **restricted privileges**: a managed-service tenant may NOT have `SYSMON`/`DBADM`, and `db2set`/instance-level reads may be blocked. (general Db2 12.1 knowledge — verify) | If supported later: expect auth failures on instance-scope functions, not missing functions |
| **Db2 Warehouse / Integrated Analytics System (IIAS)** | No | LUW-derived, **column-organized (BLU) by default**; MON_GET_* present but workload is OLAP/columnar — `POOL_COL_*`, `TOTAL_COL_*`, synopsis metrics dominate (`db2-live-pkgcache.md:275,291,327`). MPP/DPF topology is normal here. (general — verify) | Different metric emphasis; same API family |
| **Db2 for z/OS** | **No — explicitly out of scope** | **Completely different monitoring surface.** No `MON_GET_*` LUW table functions; uses IFCID/traces, `SYSIBM` catalog differs, no `SYSIBMADM.DBCFG`/`DBMCFG`. Version scheme differs (e.g. Db2 13 for z/OS). | Do NOT reuse any SQL from this plan for z/OS |

**Statement for the plan:** all SQL, column lists, function names, and gating logic in this
research target **Db2 LUW**. z/OS would require a separate integration. Db2 on Cloud and Warehouse
*could* be supported with the same SQL but differ in privileges (Cloud) and metric emphasis
(Warehouse, columnar/MPP).

---

## 8. pureScale-only telemetry (CF / GBP / FCM) — present-but-empty on non-pureScale

These functions **exist on all LUW editions** (they're in `_raw/01`) but return **rows only on a
pureScale cluster**. On the live single-member community instance they yield no useful data.

| Function (in `_raw/01`) | Line | Returns data only on | Carries |
|---|---|---|---|
| `MON_GET_CF` | `:20` | pureScale | Cluster Caching Facility state/usage |
| `MON_GET_CF_CMD` | `:21` | pureScale | CF command stats |
| `MON_GET_CF_WAIT_TIME` | `:22` | pureScale | CF wait times |
| `MON_GET_GROUP_BUFFERPOOL` | `:32` | pureScale | Group buffer pool (GBP) metrics |
| `MON_GET_FCM` | `:30` | pureScale / DPF | Fast Communication Manager |
| `MON_GET_FCM_CONNECTION_LIST` | `:31` | pureScale / DPF | FCM connections |
| `MON_GET_EXTENDED_LATCH_WAIT` | `:28` | any (but CF latches only on pureScale) | latch waits |

SYSIBMADM analogs (`_raw/03`): `DB2_CF` (`:21`), `DB2_CLUSTER_HOST_STATE` (`:22`), `DB2_MEMBER`
(`:23`), `ENV_CF_SYS_RESOURCES` (`:28`), `SNAPFCM`/`SNAPFCM_PART` (`:68-69`).

**Existing code precedent (the right pattern):** the current check emits **group buffer pool hit
ratios only when the `pool_*_gbp_l_reads` columns are non-zero**, i.e. it data-gates on the value,
not on edition detection:
- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:232-235` (column GBP)
- `:269-272` (data GBP), `:306-309` (index GBP), `:343-346` (xda GBP), `:365-377` (overall GBP)
- The GBP read columns are already SELECTed in `queries.py:55-77`
  (`pool_*_gbp_l_reads` / `pool_*_gbp_p_reads`) — they come back `0`/NULL on non-pureScale and the
  check skips the ratio gauge (`# no cov` markers confirm these branches are untested = never hit
  on the single-member test env).

**Guidance:** for any new CF/GBP/FCM metric, mirror this: call the function unconditionally, and
**skip emission when the result set is empty or the cluster columns are 0/NULL**. Optionally detect
pureScale once (§3.5) to suppress the calls entirely and avoid per-interval overhead.

---

## 9. HADR-only telemetry — present-but-empty on non-HADR

`MON_GET_HADR` (`_raw/01:33`) and `SYSIBMADM.SNAPHADR` (`_raw/03:70`) exist on all LUW editions but
return **rows only when HADR is configured** (the database is a primary or standby in an HADR pair).

| Function/view | Returns data only on | Carries (general Db2 12.1 knowledge — verify column names) |
|---|---|---|
| `MON_GET_HADR(-1)` | HADR-enabled DB | `HADR_ROLE` (PRIMARY/STANDBY), `HADR_STATE` (PEER/REMOTE_CATCHUP/…), `HADR_SYNCMODE` (SYNC/NEARSYNC/ASYNC/SUPERASYNC), `HADR_CONNECT_STATUS`, `HADR_LOG_GAP`, `PRIMARY_LOG_TIME`, `STANDBY_LOG_TIME`, `STANDBY_REPLAY_LOG_TIME`, log-position LSNs |
| `SYSIBMADM.SNAPHADR` | HADR-enabled DB | legacy snapshot equivalent |

**Detect once:** `SELECT count(*) FROM TABLE(MON_GET_HADR(-1))` > 0 → HADR active. Then emit
replication-lag / role / sync-mode metrics. On the live standalone server this is 0 rows, so HADR
metrics would be silently skipped — same empty-result pattern as §8.

Note the existing `utils.py:13-20` `DB_STATUS_MAP` already anticipates standby roles
(`ACTIVE_STANDBY`, `STANDBY`) for the service check, so HADR-awareness partly exists.

---

## 10. FEATURE-AVAILABILITY MATRIX (the deliverable)

Legend: **✅ present & returns data** on the live LUW 12.1.4 Community standalone server;
**◐ present but empty** (function/view exists, returns 0 rows without the topology);
**❓ verify** (not confirmed live). All rows are LUW; columns are edition/topology axes.

| Feature / source | LUW Community (live) | LUW ESE/AESE standalone | LUW + pureScale | LUW + DPF | LUW + HADR | Gate / how to guard |
|---|---|---|---|---|---|---|
| Version detect (`SYSVERSIONS`, `ENV_INST_INFO`) | ✅ | ✅ | ✅ | ✅ | ✅ | always available |
| Edition detect (`ENV_PROD_INFO`) | ✅ (DEC/COMMUNITY) | ✅ | ✅ | ✅ | ✅ | filter `LICENSE_INSTALLED='Y'` |
| Config reads (`DBCFG`/`DBMCFG`/`REG_VARIABLES`) | ✅ | ✅ | ✅ (per-member rows) | ✅ (per-member rows) | ✅ | filter `member=0` or keep member dim (`db2-config-settings.md:100-114`) |
| Query metrics (`MON_GET_PKG_CACHE_STMT`) | ✅ 327 cols | ✅ | ✅ | ✅ | ✅ | runtime col introspection (§5); `EXECUTE` grant |
| Samples (`MON_CURRENT_SQL`/`MON_GET_ACTIVITY`) | ✅ | ✅ | ✅ | ✅ | ✅ | exclude self handle; gate timing on `mon_act_metrics` |
| Transactions (`MON_GET_UNIT_OF_WORK`) | ✅ | ✅ | ✅ | ✅ | ✅ | no STMT_TEXT (`db2-live-activity.md:103`) |
| Connections (`MON_GET_CONNECTION`) | ✅ | ✅ | ✅ | ✅ | ✅ | identity join source |
| System metrics (`MON_GET_DATABASE/INSTANCE/BUFFERPOOL/TABLESPACE/TRANSACTION_LOG`) | ✅ | ✅ | ✅ | ✅ | ✅ | already in `queries.py` |
| EXPLAIN / plan capture (`EXPLAIN_OPERATOR`) | ✅ (`_raw/05`) | ✅ | ✅ | ✅ | ✅ | needs EXPLAIN tables + privilege |
| Lock waits (`MON_GET_LOCKS`, `MON_GET_APPL_LOCKWAIT`, `MON_LOCKWAITS`) | ✅ (present) | ✅ | ✅ | ✅ | ✅ | gate detail on `mon_lockwait`/`mon_lck_msg_lvl` (§6) |
| **CF metrics** (`MON_GET_CF`, `MON_GET_CF_CMD`, `MON_GET_CF_WAIT_TIME`, `DB2_CF`) | ◐ empty | ◐ empty | ✅ | ◐ empty | ◐ empty | §3.5 detect; skip on empty |
| **Group buffer pool** (`MON_GET_GROUP_BUFFERPOOL`, `pool_*_gbp_*`) | ◐ empty/0 | ◐ empty/0 | ✅ | ◐ | ◐ | data-gate on non-zero `*_gbp_*` (existing pattern, §8) |
| **FCM** (`MON_GET_FCM`, `MON_GET_FCM_CONNECTION_LIST`, `SNAPFCM`) | ◐ (single-node trivial) | ◐ | ✅ | ✅ | ◐ | meaningful only multi-member |
| **HADR** (`MON_GET_HADR`, `SNAPHADR`) | ◐ empty | ◐ empty | ◐/✅ | ◐ | ✅ | §3.6 detect; skip on empty |
| Member/cluster state (`DB2_MEMBER`, `DB2_CLUSTER_HOST_STATE`) | ✅ (1 member row) | ✅ | ✅ (multi rows + CF) | ✅ (multi rows) | ✅ | row count = topology signal |
| WLM service-class/workload (`MON_GET_SERVICE_SUBCLASS`, `MON_GET_WORKLOAD`, …) | ✅ (default classes) | ✅ | ✅ | ✅ | ✅ | always present; richer with WLM configured |
| Routine metrics (`MON_GET_ROUTINE`, `_DETAILS`, `_EXEC_LIST`) | ✅ present | ✅ | ✅ | ✅ | ✅ | `_EXEC_LIST` gated by `mon_rtn_execlist` (live `OFF`, `_raw/04:18`) |
| `*_DETAILS` XML variants (`MON_GET_PKG_CACHE_STMT_DETAILS`, etc.) | ❓ (present, not callable as db2inst1 in probe) | ❓ | ❓ | ❓ | ❓ | verify grants/signature; not needed for core (`db2-live-pkgcache.md:401-409`) |
| Model-provider waits (`MODEL_PROVIDER_*`) | ✅ (12.1 col) | ✅ (12.1) | ✅ | ✅ | ✅ | **absent < 12.1** → col introspection (§5) |
| 12.1 caching-tier / columnar `POOL_COL_*` cols | ✅ (12.1) | ✅ | ✅ | ✅ | ✅ | additive cols; introspect (§5) |

---

## 11. Concrete gating recommendations for the plan

1. **One-time capability probe at connection setup**, cached for the connection lifetime, storing:
   - `versionnumber` (packed int) and `service_level` (string),
   - `installed_prod` + `license_type` (edition),
   - `is_purescale` (CF rows > 0, §3.5), `is_dpf` (`num_dbpartitions > 1`),
     `is_hadr` (`MON_GET_HADR` rows > 0, §3.6), `member_count`,
   - the `mon_*_metrics` levels (§6).
   Tag emitted telemetry with `db2_version`, `db2_edition`, and topology booleans.
2. **Prefer runtime column introspection over version branching** for every MON_GET-based
   collector (§5). Only use `versionnumber` comparisons to *label* version-specific metrics or to
   skip a known-absent function entirely.
3. **Tolerate empty result sets** for CF/GBP/FCM (§8) and HADR (§9) — mirror the existing
   non-pureScale GBP skip pattern (`ibm_db2.py:232-377`). Optionally suppress the calls when the
   one-time topology probe says standalone/non-HADR.
4. **Gate timing-derived fields on `mon_*_metrics`** (§6), independent of version/edition.
5. **Do not gate any feature off Community Edition** (§4) — Community gets the full DBM surface.
6. **Privilege gating:** the monitoring user needs `EXECUTE` on the called routines or one of
   `SYSMON` / `DATAACCESS` / `DBADM` / `SQLADM`; `SYSMON` is the least-privilege recommendation that
   covers MON_GET_* + config + ENV views (`db2-config-settings.md:305-312`,
   `db2-live-pkgcache.md:406-409`, `db2-live-activity.md:508-510`). On Db2 on Cloud expect some of
   these to be unavailable (§7).
7. **Scope guard:** all of the above is **LUW only**. If a z/OS target ever appears, none of these
   SQL paths apply (§7).

---

## 12. Source index

### Live-empirical (authoritative for 12.1.4 Community)
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/01-version-and-monget-functions.txt`
  — server string `DB2/LINUXX8664 12.1.4.0`, 64 MON_GET functions present.
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/03-sysibmadm-objects.txt`
  — 79 SYSIBMADM views present (incl. `DB2_CF`, `DB2_MEMBER`, `SNAPHADR`, `ENV_*`, `SNAPFCM`).
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/04-monitor-config.txt`
  — live `mon_*_metrics` collection levels.
- `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/_raw/05-explain-test.txt`
  — EXPLAIN works on Community; `EXPLAIN_OPERATOR` cost schema.
- Sibling findings: `db2-live-pkgcache.md` (327-col pkg cache), `db2-live-activity.md` (418-col
  activity + views), `db2-config-settings.md` (version/edition/config detection SQL — §6 there is
  the canonical detection reference).

### Code (absolute paths)
- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28` — driver version fetch.
- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:109-125` — version parse;
  `:232-235,269-272,306-309,343-346,365-377` — existing pureScale GBP data-gating pattern (the model
  to follow for cluster-only telemetry); `:13-20` (utils) — standby roles in `DB_STATUS_MAP`.
- `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py` — current system-metric
  queries (`MON_GET_INSTANCE/DATABASE/BUFFERPOOL/TABLESPACE/TRANSACTION_LOG`); GBP read columns at `:55-77`.

### IBM / web (semantics — verify against 12.1; KC URLs 403 to automated fetchers)
- ENV_PROD_INFO / edition codes, ENV_INST_INFO version columns, SYSVERSIONS packed number — see
  `db2-config-settings.md` §6 citations (IBM 11.1/11.5 doc pages document the same view schemas;
  values verified live on 12.1.4).
- MON_GET_HADR / MON_GET_CF / MON_GET_GROUP_BUFFERPOOL / MON_GET_FCM — IBM Db2 12.1 monitor table
  function reference (column lists for HADR/CF/GBP/FCM marked "verify" above were not captured live
  because the standalone server returns 0 rows).
