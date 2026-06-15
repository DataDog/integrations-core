# Db2 CONFIGURATION / SETTINGS Exposure — Research for a DBM "settings" Payload

Raw research input for the Db2 DBM implementation plan. Target Db2 version: **12.1** (live container
**12.1.4.0**, image `icr.io/db2_community/db2:12.1.4.0`, container `db2-primary`). All "live" column
lists and sample values in this doc were obtained by querying that running container directly (cited
inline as `[LIVE]`). Web findings cite URLs. Code findings cite absolute paths.

> **Scope.** This file documents *how to read every layer of Db2 configuration via SQL* so a DBM
> "settings" collector can emit a `dbm-metadata` event of `kind: "db2_settings"` (and optionally
> separate `kind`s for registry vars / env info), plus how to detect Db2 **version / edition / build**
> in SQL. It is the Db2 analog of postgres `pg_settings` collection
> (`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/metadata.py:48-61, 206-291`),
> mysql `mysql_variables` (`/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/metadata.py:31,185`),
> and sqlserver `sqlserver_configs` (`/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/metadata.py:128-161`).

---

## 0. TL;DR — the four configuration layers and how to read each in SQL

Db2 LUW configuration is layered. A high-fidelity "settings" payload should capture all four:

| Layer | What it is | SQL read path (preferred, SYSIBMADM view) | Underlying table function | Live row count (12.1.4) |
|---|---|---|---|---|
| **DBM CFG** | Database **manager** (instance-level) config — applies to the whole instance | `SYSIBMADM.DBMCFG` | `SYSPROC.DBM_GET_CFG()` | **113** rows `[LIVE]` |
| **DB CFG** | Database (per-database) config — applies to the connected DB | `SYSIBMADM.DBCFG` | `SYSPROC.DB_GET_CFG()` | **194** rows `[LIVE]` |
| **Registry / env vars** | `db2set` profile registry + OS env vars | `SYSIBMADM.REG_VARIABLES` | `SYSPROC.REG_LIST_VARIABLES()` | **3** rows `[LIVE]` (startup-time only — see §3.4) |
| **Environment / build** | Instance/system/product/feature info (version, edition, OS, CPUs, memory, license) | `SYSIBMADM.ENV_INST_INFO`, `ENV_SYS_INFO`, `ENV_PROD_INFO`, `ENV_FEATURE_INFO` | `SYSPROC.ENV_GET_*` | — |

All four require a **database connection** (these are SQL views, not commands). The `db2 get dbm cfg` /
`db2set` *commands* do not need a connection, but the *SQL views* do — relevant because the existing
`ibm_db2` check already holds a persistent connection (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:554-578`).

Recommended single "settings" payload shape (mirrors pg/mysql/sqlserver): one `dbm-metadata` event with
`kind: "db2_settings"` whose `metadata` array is the **union of DBM CFG + DB CFG rows**, each row tagged
with which config it came from. Registry vars and ENV/version info are best emitted as their own
sub-events (`kind: "db2_registry_variables"`, and the version/edition folded into the
`database_instance` event's `dbms_version` per §6).

---

## 1. DBM CFG — `SYSIBMADM.DBMCFG` (database manager / instance config)

### 1.1 Exact columns (live, Db2 12.1.4 `SYSCAT.COLUMNS`) `[LIVE]`

Query used: `select colname, typename, length from syscat.columns where tabschema='SYSIBMADM' and tabname='DBMCFG' order by colno`

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `NAME` | VARCHAR | 32 | dbm cfg parameter name, lowercase (e.g. `svcename`, `diaglevel`, `numdb`, `instance_memory`, `sheapthres`, `intra_parallel`, `fcm_num_buffers`) |
| 2 | `VALUE` | VARCHAR | 1024 | current **in-memory** value |
| 3 | `VALUE_FLAGS` | VARCHAR | 10 | flag for `VALUE`; observed domain `{NONE, AUTOMATIC}` `[LIVE]` |
| 4 | `DEFERRED_VALUE` | VARCHAR | 1024 | value **on disk** — takes effect after `db2stop`/`db2start` |
| 5 | `DEFERRED_VALUE_FLAGS` | VARCHAR | 10 | flag for deferred value; `{NONE, AUTOMATIC}` |
| 6 | `DATATYPE` | VARCHAR | 128 | declared datatype of the parameter, e.g. `INTEGER`, `BIGINT`, `SMALLINT`, `VARCHAR(n)` |

Note: **DBMCFG has no `DBPARTITIONNUM`/`MEMBER` column** (dbm cfg is instance-wide). DBCFG does (§2.1).

### 1.2 Canonical read query

```sql
SELECT name, value, value_flags, deferred_value, deferred_value_flags, datatype
FROM SYSIBMADM.DBMCFG
ORDER BY name;
```

### 1.3 Live sample (selected rows) `[LIVE]`

```
diaglevel        3
fcm_num_buffers  4096
intra_parallel   NO
jdk_path         /database/config/db2inst1/sqllib/java/jdk64
numdb            32
sheapthres       0
svcename         db2c_db2inst1
```

### 1.4 Reference

- IBM: DBMCFG administrative view (11.5; column set unchanged in 12.1) —
  https://www.ibm.com/docs/en/db2/11.5.x?topic=views-dbmcfg-database-manager-configuration-parameter-information
- The view = `SYSPROC.DBM_GET_CFG()` table function. Returns in-memory + on-disk values.

---

## 2. DB CFG — `SYSIBMADM.DBCFG` (per-database config)

### 2.1 Exact columns (live, Db2 12.1.4) `[LIVE]`

Query used: `select colname, typename, length from syscat.columns where tabschema='SYSIBMADM' and tabname='DBCFG' order by colno`

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `NAME` | VARCHAR | 32 | db cfg parameter name, lowercase (e.g. `database_memory`, `logpath`, `locklist`, `sortheap`, `auto_runstats`) |
| 2 | `VALUE` | VARCHAR | 1024 | current in-memory value |
| 3 | `VALUE_FLAGS` | VARCHAR | 10 | flag for value; `{NONE, AUTOMATIC}` `[LIVE]` |
| 4 | `DEFERRED_VALUE` | VARCHAR | 1024 | value on disk; takes effect after DB deactivate/activate (or connection reset) |
| 5 | `DEFERRED_VALUE_FLAGS` | VARCHAR | 10 | flag for deferred value; `{NONE, AUTOMATIC}` |
| 6 | `DATATYPE` | VARCHAR | 128 | parameter datatype |
| 7 | `DBPARTITIONNUM` | SMALLINT | 2 | database partition number (DPF). Single-node → `0` |
| 8 | `MEMBER` | SMALLINT | 2 | member number (pureScale / member topology). Single-node → `0` |

DBCFG **adds `DBPARTITIONNUM` and `MEMBER`** vs DBMCFG. On a single-node instance both are `0`; on
DPF/pureScale you get **one row per parameter per member**, so a naive `SELECT *` multiplies rows by
member count. Filter to a single member (`WHERE member = 0` or `WHERE dbpartitionnum = 0`) or carry the
member as a row dimension.

### 2.2 Canonical read query (single-member)

```sql
SELECT name, value, value_flags, deferred_value, deferred_value_flags, datatype, dbpartitionnum, member
FROM SYSIBMADM.DBCFG
WHERE member = 0           -- collapse multi-member topologies; drop this to capture all members
ORDER BY name;
```

### 2.3 Live `VALUE_FLAGS` / `DATATYPE` domains `[LIVE]`

- `VALUE_FLAGS` and `DEFERRED_VALUE_FLAGS`: only `NONE` and `AUTOMATIC` observed. `AUTOMATIC` means the
  parameter is self-tuning (STMM / autonomic), e.g. `applheapsz`, `avg_appls`. When `AUTOMATIC`, the
  numeric `VALUE` is the *current computed* value; the flag is the load-bearing signal.
- `DATATYPE` distinct values observed: `BIGINT`, `INTEGER`, `SMALLINT`, and many `VARCHAR(n)` widths
  (`VARCHAR(3)`…`VARCHAR(2048)`).

### 2.4 Detecting **pending** (uncommitted) config changes

Where `VALUE != DEFERRED_VALUE`, a change is staged but not yet active (needs DB deactivate/activate or
instance restart). This is the Db2 analog of postgres `pending_restart` (postgres exposes a boolean
column; Db2 you compute it). Useful to surface as a derived `pending_change: true` per row, or as a
union diagnostic:

```sql
SELECT name, value AS current_value, deferred_value AS pending_value
FROM SYSIBMADM.DBCFG  WHERE value <> deferred_value
UNION ALL
SELECT name, value, deferred_value
FROM SYSIBMADM.DBMCFG WHERE value <> deferred_value
ORDER BY 1;
```
Source: dbi-software pending-changes pattern — https://www.dbisoftware.com/blog/db2_performance.php?print=161

### 2.5 Reference

- IBM: DBCFG administrative view and DB_GET_CFG table function (11.5; columns unchanged in 12.1) —
  https://www.ibm.com/docs/en/db2/11.5.x?topic=views-dbcfg-database-configuration-parameter-information

---

## 3. Registry / environment variables — `SYSIBMADM.REG_VARIABLES`

### 3.1 Exact columns (live, Db2 12.1.4) `[LIVE]`

Query used: `select colname, typename, length from syscat.columns where tabschema='SYSIBMADM' and tabname='REG_VARIABLES' order by colno`

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `DBPARTITIONNUM` | SMALLINT | 2 | partition the value applies to. Single-node → `0` |
| 2 | `REG_VAR_NAME` | VARCHAR | 256 | registry/env variable name (e.g. `DB2COMM`, `DB2SYSTEM`, `DB2_FED_LIBPATH`) |
| 3 | `REG_VAR_VALUE` | VARCHAR | 2048 | the value (uppercase name, value as-is) |
| 4 | `IS_AGGREGATE` | SMALLINT | 2 | `1` if this is an aggregate registry var (a group/macro var), else `0` |
| 5 | `AGGREGATE_NAME` | VARCHAR | 256 | name of the aggregate group, if `IS_AGGREGATE`/member of one |
| 6 | `LEVEL` | CHARACTER | 1 | which profile registry the value came from (see §3.3) |

### 3.2 Canonical read query

```sql
SELECT reg_var_name, reg_var_value, level, is_aggregate, aggregate_name, dbpartitionnum
FROM SYSIBMADM.REG_VARIABLES
ORDER BY reg_var_name;
```

### 3.3 `LEVEL` column code → meaning (single-char)

| Code | Profile registry level | Notes |
|---|---|---|
| `E` | **Environment** variable (OS-level `set`/export) | highest precedence at runtime |
| `N` | Instance **node**-level registry (`db2set -i <inst> <node>`) | DPF only |
| `I` | **Instance**-level registry (`db2set -i` / plain `db2set`) | most vars live here |
| `G` | **Global**-level registry (`db2set -g`) | machine-wide; some vars (e.g. `DB2SYSTEM`, `DB2INSTDEF`) are global-only |

Resolution precedence (low overrides high): Environment > Instance-node > Instance > Global.
Source: https://www.databasejournal.com/db2/understanding-ibm-db2-db2set/ ;
https://datageek.blog/2017/08/22/db2-basics-levels-of-configuration/

### 3.4 IMPORTANT caveat — REG_VARIABLES is **startup-time only**

`SYSIBMADM.REG_VARIABLES` returns the registry values **that were in effect when the instance was
started**, NOT live values. If an operator runs `db2set FOO=bar` after `db2start`, the view will not
reflect it until the next instance restart. This means it can **disagree with `db2set -all`**.

Confirmed `[LIVE]`: the container's `db2set -all` returns only `[i] DB2COMM=TCPIP` and
`[g] DB2SYSTEM=db2-primary` (2 vars), but `SYSIBMADM.REG_VARIABLES` returns **3** rows — it additionally
shows `DB2_FED_LIBPATH` with `LEVEL=E` (an environment-level value present at instance start). So the
view is the *startup snapshot* including env-derived values; `db2set -all` is the *current profile
registry* and omits pure-environment vars. Both are useful; the SQL view is what a connection-only
collector can reach. Document this skew in the payload (e.g. a note that registry vars reflect last
instance start).

Live REG_VARIABLES rows `[LIVE]`:
```
REG_VAR_NAME      REG_VAR_VALUE                         IS_AGG  AGG  LEVEL
DB2COMM           TCPIP                                 0       -    I
DB2SYSTEM         db2-primary                           0       -    G
DB2_FED_LIBPATH   /database/config/db2inst1/sqll...     0       -    E
```

### 3.5 Reference

- IBM: REG_VARIABLES administrative view —
  https://www.ibm.com/docs/en/db2/11.5.x?topic=routines-reg-variables-administrative-view (and the
  `REG_LIST_VARIABLES` table function). Startup-time caveat documented across IBM + community sources.

---

## 4. Environment / build / edition views (version + host facts)

These four `SYSIBMADM` views (backed by `SYSPROC.ENV_GET_*` table functions) carry the data needed for
`dbms_version`, edition detection, and host facts. Columns below are **live from 12.1.4** `[LIVE]`.

### 4.1 `SYSIBMADM.ENV_INST_INFO` — instance / version / build (MOST IMPORTANT for version detection)

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `INST_NAME` | VARCHAR | 128 | instance name (e.g. `db2inst1`) |
| 2 | `IS_INST_PARTITIONABLE` | SMALLINT | 2 | `1` if DPF-capable instance |
| 3 | `NUM_DBPARTITIONS` | INTEGER | 4 | number of DB partitions |
| 4 | `INST_PTR_SIZE` | INTEGER | 4 | bitness (`64`) |
| 5 | `RELEASE_NUM` | VARCHAR | 128 | internal release code (e.g. `02050110`) |
| 6 | `SERVICE_LEVEL` | VARCHAR | 128 | **human version string** (e.g. `DB2 v12.1.4.0`) — primary version source |
| 7 | `BLD_LEVEL` | VARCHAR | 128 | build level (e.g. `s2602211313`) |
| 8 | `PTF` | VARCHAR | 128 | PTF identifier (e.g. `DYN2602211`) |
| 9 | `FIXPACK_NUM` | INTEGER | 4 | fix pack number (e.g. `0`) |
| 10 | `NUM_MEMBERS` | INTEGER | 4 | number of members |

Live row `[LIVE]`:
```
INST_NAME=db2inst1  IS_INST_PARTITIONABLE=0  NUM_DBPARTITIONS=1  INST_PTR_SIZE=64
RELEASE_NUM=02050110  SERVICE_LEVEL="DB2 v12.1.4.0"  BLD_LEVEL=s2602211313
PTF=DYN2602211  FIXPACK_NUM=0  NUM_MEMBERS=1
```

### 4.2 `SYSIBMADM.ENV_PROD_INFO` — installed products / **edition** / license

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `INSTALLED_PROD` | VARCHAR | 26 | product code (e.g. `ESE`, `DEC`, `STD`, `ADV`, `AESE`, `AWSE`, `WSE`, `DAE`, `DSE`, `STARTER`, `LITE`, `BASE`, `ADV_AI`, `STD_AI`) |
| 2 | `INSTALLED_PROD_FULLNAME` | VARCHAR | 100 | full product name |
| 3 | `LICENSE_INSTALLED` | CHARACTER | 1 | `Y`/`N` — whether the license for this product is installed |
| 4 | `PROD_RELEASE` | VARCHAR | 26 | release (e.g. `12.1`) |
| 5 | `LICENSE_TYPE` | VARCHAR | 50 | license type string (e.g. `COMMUNITY`) |

**Edition detection:** filter to the row where `LICENSE_INSTALLED='Y'`. On the live community container
`[LIVE]` the only `Y` row is `INSTALLED_PROD=DEC`, `LICENSE_TYPE=COMMUNITY` (DEC = "Db2 Community
Edition"); all other product rows are `N`. So:
```sql
SELECT installed_prod, prod_release, license_type
FROM SYSIBMADM.ENV_PROD_INFO
WHERE license_installed = 'Y';
```
returns the active edition. (This view always lists **all** known product codes; license flag is the
discriminator.)

### 4.3 `SYSIBMADM.ENV_SYS_INFO` — host / OS / CPU / memory

| Col # | Column | Type | Len | Meaning | Live value `[LIVE]` |
|---|---|---|---|---|---|
| 1 | `OS_NAME` | VARCHAR | 256 | OS name | `Linux` |
| 2 | `OS_VERSION` | VARCHAR | 256 | OS version | `6` |
| 3 | `OS_RELEASE` | VARCHAR | 256 | OS release | `8` |
| 4 | `HOST_NAME` | VARCHAR | 255 | host name | `db2-primary` |
| 5 | `TOTAL_CPUS` | BIGINT | 8 | total CPUs | `16` |
| 6 | `CONFIGURED_CPUS` | BIGINT | 8 | configured CPUs | `16` |
| 7 | `TOTAL_MEMORY` | BIGINT | 8 | total memory **in MB** | `63592` |
| 8 | `OS_FULL_VERSION` | VARCHAR | 256 | full OS version | — |
| 9 | `OS_KERNEL_VERSION` | VARCHAR | 256 | kernel version | — |
| 10 | `OS_ARCH_TYPE` | VARCHAR | 256 | architecture | `x86_64` |

(`OS_FULL_VERSION`, `OS_KERNEL_VERSION`, `OS_ARCH_TYPE` are newer columns present in 12.1; older
docs/versions may show only the first 7. Treat the last 3 as version-conditional and `SELECT` defensively.)

### 4.4 `SYSIBMADM.ENV_FEATURE_INFO` — licensed feature usage

| Col # | Column | Type | Len | Meaning |
|---|---|---|---|---|
| 1 | `FEATURE_NAME` | VARCHAR | 26 | feature code |
| 2 | `FEATURE_FULLNAME` | VARCHAR | 100 | feature full name |
| 3 | `LICENSE_INSTALLED` | CHARACTER | 1 | `Y`/`N` |
| 4 | `PRODUCT_NAME` | VARCHAR | 26 | owning product |
| 5 | `FEATURE_USE_STATUS` | VARCHAR | 30 | usage status |

Live: returns **0 rows** on the community container `[LIVE]` (no licensed features). Treat as optional.

### 4.5 References

- IBM: ENV_INST_INFO administrative view —
  https://www.ibm.com/docs/en/db2/11.1.0?topic=views-env-inst-info-current-instance-information
- Useful overview of ENV_* views — https://blog.4loeser.net/2014/11/useful-db2-administrative-functions-and.html

---

## 5. Authorization / privileges required

These views require a connection plus authority on the underlying routine. From IBM's authorization
model for `SYSIBMADM` config/monitoring views, the caller needs **one of** the following data-access
authorities (any one suffices), plus the implicit `SELECT` on the view (granted to PUBLIC by default in
a non-restrictive DB):

- `DBADM`, or `SQLADM`, or `SYSADM`/`SYSCTRL`/`SYSMAINT`, or **`SYSMON`** (the least-privileged, intended
  for monitoring) — `SYSMON` is the right one to recommend for a read-only DBM user.
- EXECUTE on the backing routines: `SYSPROC.DBM_GET_CFG`, `SYSPROC.DB_GET_CFG`,
  `SYSPROC.REG_LIST_VARIABLES`, `SYSPROC.ENV_GET_INST_INFO`, `SYSPROC.ENV_GET_SYS_INFO`,
  `SYSPROC.ENV_GET_PROD_INFO`, `SYSPROC.ENV_GET_FEATURE_INFO`.

The existing integration's setup guidance already grants `EXECUTE` on the five MON_GET table functions or
one of `DATAACCESS`/`DBADM`/`SQLADM`
(`/home/bits/dd/integrations-core/ibm_db2/README.md:58-106`); for settings collection, **extend that to
include EXECUTE on the config/env routines above, or recommend `SYSMON`** (covers all of them). Note:
on the live community container the check connects as `db2inst1` (the instance owner) which has full
authority, so settings queries succeed there without extra grants.

References:
- General SYSIBMADM authorization model — https://www.ibm.com/docs/en/db2/11.1.0?topic=views-privileges-privilege-information
- DataGeek authorities cookbook — https://datageek.blog/2018/04/19/db2-administrative-sql-cookbook-listing-database-authorities-that-an-idgroup-holds/

---

## 6. Db2 version / edition / build detection in SQL (for `dbms_version`)

Multiple equivalent paths exist. Recommended primary + fallbacks:

### 6.1 Primary: `SYSIBMADM.ENV_INST_INFO` (rich, one row)
```sql
SELECT service_level, bld_level, fixpack_num, release_num, num_members
FROM SYSIBMADM.ENV_INST_INFO;
-- live: SERVICE_LEVEL='DB2 v12.1.4.0', BLD_LEVEL='s2602211313', FIXPACK_NUM=0
```
`SERVICE_LEVEL` (`DB2 v12.1.4.0`) is the canonical human version string and maps 1:1 to `db2level`.
Parse the `VV.RR.MM.FF` four-part signature from the `vXX.X.X.X` token → `db2_version="12.1.4.0"`
(the existing check already parses the `MM.mm.uuuu` form via the driver API in
`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:109-125`).

### 6.2 Table-function form (no view dependency)
```sql
SELECT service_level, fixpack_num FROM TABLE(SYSPROC.ENV_GET_INST_INFO());
-- live: 'DB2 v12.1.4.0', 0
```

### 6.3 Numeric version (easy comparisons)
```sql
SELECT versionnumber, version_timestamp FROM SYSIBM.SYSVERSIONS;
-- live: VERSIONNUMBER=12010400  (= 12.01.04.00), VERSION_TIMESTAMP=2026-06-13-01.01.22
```
`versionnumber` is a packed integer (`VVRRMMFF` → `12010400`), trivially `>=`/`<` comparable for
feature gating across 11.5 vs 12.1.

### 6.4 Edition / product
```sql
SELECT installed_prod, prod_release, license_type
FROM SYSIBMADM.ENV_PROD_INFO WHERE license_installed = 'Y';
-- live: INSTALLED_PROD='DEC', PROD_RELEASE='12.1', LICENSE_TYPE='COMMUNITY'
-- or table function: TABLE(SYSPROC.ENV_GET_PROD_INFO())
```

### 6.5 `MON_GET_INSTANCE` also carries version/platform (already used by the check)
`TABLE(MON_GET_INSTANCE(-1))` columns include (live header `[LIVE]`):
`MEMBER, DB2_STATUS, DB2START_TIME, TIMEZONEOFFSET, TIMEZONEID, CON_LOCAL_DBASES, TOTAL_CONNECTIONS,
AGENTS_REGISTERED, AGENTS_REGISTERED_TOP, IDLE_AGENTS, AGENTS_FROM_POOL, AGENTS_CREATED_EMPTY_POOL,
NUM_COORD_AGENTS, COORD_AGENTS_TOP, AGENTS_STOLEN, GW_TOTAL_CONS, GW_CUR_CONS, GW_CONS_WAIT_HOST,
GW_CONS_WAIT_CLIENT, NUM_GW_CONN_SWITCHES, PRODUCT_NAME, SERVICE_LEVEL, SERVER_PLATFORM,
NETWORK_INTERFACE_BOUND` (plus more). So `PRODUCT_NAME` (`DB2 v12.1.4.0` `[LIVE]`), `SERVICE_LEVEL`
(`s2602211313 (DYN2602211313AMD64)` `[LIVE]`), and `SERVER_PLATFORM` (`Linux/X8664` `[LIVE]`) are
available without an extra view. The current check only reads `total_connections` from this function
(`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py:15-17`).

### 6.6 Driver-level fallback (no SQL)
The existing check uses the `ibm_db` driver API:
`ibm_db.get_db_info(connection, ibm_db.SQL_DBMS_VER)` → raw `MM.mm.uuuu`
(`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28`). Keep as a fallback.

References:
- db2level / version detection — https://datageek.blog/2012/06/12/db2-commands-db2level/
- ENV_INST_INFO version columns — https://www.ibm.com/docs/en/db2/11.1.0?topic=views-env-inst-info-current-instance-information

---

## 7. 11.5 vs 12.1 differences (call-outs)

The **column layouts of DBCFG/DBMCFG/REG_VARIABLES are stable across 11.5 → 12.1** (verified live on
12.1.4 against the documented 11.5 schemas — same 6 cols for DBMCFG, 8 for DBCFG, 6 for REG_VARIABLES).
What changes is the **set of parameter rows**, not the view shape:

- **Row count grows.** Live 12.1.4: 113 DBMCFG params, 194 DBCFG params. New parameters appear in 12.1
  (and within fix packs). A settings collector must be **schema-agnostic over rows** (just select all
  rows) and not hard-code a parameter list — DO NOT assume a fixed set.
- **`ENV_SYS_INFO`** gained `OS_FULL_VERSION`, `OS_KERNEL_VERSION`, `OS_ARCH_TYPE` (present in 12.1;
  may be absent in older builds). Select columns defensively or `SELECT *` and tolerate missing keys.
- **`ENV_PROD_INFO`** product-code list expanded over time (12.1 includes AI editions `ADV_AI`,
  `STD_AI`, plus `DEC`/`STARTER`/`LITE` etc.). Don't enumerate codes; filter by `LICENSE_INSTALLED='Y'`.
- **Per-member multiplication:** DBCFG/REG_VARIABLES carry `DBPARTITIONNUM`/`MEMBER`; pureScale/DPF
  topologies return one row per member. The existing metrics check always passes `-1`/`NULL` to MON_GET
  functions to aggregate across members (`/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:99`);
  for settings, either filter `member=0` or keep member as a row dimension.
- **`VALUE_FLAGS`/`DEFERRED_VALUE_FLAGS`** semantics (`AUTOMATIC`/`NONE`) are unchanged across versions.

To **gate features by version** in code, prefer the packed integer from `SYSIBM.SYSVERSIONS.versionnumber`
(`12010400`) or parse `ENV_INST_INFO.SERVICE_LEVEL`.

---

## 8. Proposed `dbm-metadata` settings payload (Db2-specific, mirrors §6.2 of the payload-contract doc)

Follow the metadata-event envelope from
`/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-dbm-payload-contract.md`
(§6.2) and the postgres implementation
(`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/metadata.py:206-226`). Cross-DBMS
`kind` precedents: postgres `pg_settings`, mysql `mysql_variables`
(`/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/metadata.py:185`), sqlserver
`sqlserver_configs` (`/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/metadata.py:150`).

### 8.1 Event envelope (use `kind: "db2_settings"`)
```python
event = {
    "host":                self._check.reported_hostname,
    "database_instance":   self._check.database_identifier,
    "agent_version":       datadog_agent.get_version(),
    "dbms":                "db2",
    "kind":                "db2_settings",
    "collection_interval": self.settings_collection_interval,   # default 600s (mirror pg)
    "dbms_version":        self._check.dbms_version,             # "12.1.4.0"
    "tags":                self._tags_no_db,                     # dd.internal + db: stripped
    "timestamp":           time.time() * 1000,                  # epoch ms
    "cloud_metadata":      self._check.cloud_metadata,
    "metadata":            settings_rows,                        # list[dict] (DBM CFG + DB CFG union)
}
self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
```

### 8.2 Per-row schema (recommended normalized shape)
Union DBMCFG + DBCFG into one array; tag the source so the backend/UI can distinguish. Suggested keys:
```python
{
  "name":                 row["name"],                       # parameter name
  "value":                row["value"],                      # current in-memory value (str)
  "value_flags":          row["value_flags"],                # "NONE" | "AUTOMATIC"
  "deferred_value":       row["deferred_value"],             # on-disk value
  "deferred_value_flags": row["deferred_value_flags"],
  "datatype":             row["datatype"],
  "config_scope":         "dbm" | "db",                      # which config it came from (derive)
  "pending_change":       row["value"] != row["deferred_value"],   # derived; Db2 analog of pg pending_restart
  # DBCFG-only: "member": row["member"]                      # include only if collecting all members
}
```
The single query to feed `metadata` (one round trip, source-tagged via UNION):
```sql
SELECT 'dbm' AS config_scope, name, value, value_flags, deferred_value, deferred_value_flags, datatype,
       CAST(NULL AS SMALLINT) AS member
FROM SYSIBMADM.DBMCFG
UNION ALL
SELECT 'db'  AS config_scope, name, value, value_flags, deferred_value, deferred_value_flags, datatype,
       member
FROM SYSIBMADM.DBCFG
WHERE member = 0
ORDER BY config_scope, name;
```

### 8.3 Optional separate events
- `kind: "db2_registry_variables"` — array of REG_VARIABLES rows (`reg_var_name`, `reg_var_value`,
  `level`, `is_aggregate`, `aggregate_name`). Add a note in the payload that values are **startup-time**
  (§3.4).
- Version/edition/host facts (ENV_INST_INFO / ENV_PROD_INFO / ENV_SYS_INFO) are best folded into the
  `dbms_version` string and the `database_instance` event rather than a separate settings event, but
  could be a `kind: "db2_env_info"` if richer host facts are desired.

### 8.4 Driver-specific extraction note
The `ibm_db` driver returns dict rows via `ibm_db.fetch_assoc` with **lowercase** keys (the check sets
`ibm_db.ATTR_CASE = ibm_db.CASE_LOWER`, `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py:567`),
so all `metadata` row keys come back lowercase already — match the schema above accordingly. Reuse the
existing `iter_rows` generator (`ibm_db2.py:610-631`) with `ibm_db.fetch_assoc`.

---

## 9. Config surface to add (mirror postgres `collect_settings`)

Postgres conf
(`/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/data/conf.yaml.example:570-587`):
```yaml
collect_settings:
  enabled: false
  collection_interval: 600          # seconds
  ignored_settings_patterns: ['plpgsql%']
```
Db2 analog — add a `collect_settings` block with `enabled`, `collection_interval` (default **600s**),
and an **`ignored_settings_patterns`** list (Db2 uses SQL `LIKE`/`NOT LIKE`; postgres applies it as
`WHERE name NOT LIKE ALL(%s)` at `metadata.py:271-280`). Default ignore list should drop noisy/sensitive
params if desired.

**Security-sensitive params to consider redacting / ignoring** (present live `[LIVE]`): DBMCFG
`sysadm_group`, `sysctrl_group`, `sysmaint_group`, `sysmon_group`, `authentication`, `srvcon_auth`,
`federated`, `keystore_location`, `keystore_type`, `ssl_svr_keydb`, `ssl_svr_stash`, `ssl_svcename`;
DBCFG path/credential-ish params. Values are config (not secrets), but groups/keystore paths leak topology
— offer pattern-based exclusion (e.g. `['%keystore%','%group%']`) and document it. Db2 cfg never stores
passwords in these views, so there's no plaintext-secret risk, but be conservative.

---

## 10. Quick verification recipe (against the live container)

All queries below confirmed to run as `db2inst1` against `testdb` on `db2-primary` (12.1.4.0) `[LIVE]`:
```bash
docker exec db2-primary su - db2inst1 -c \
  "db2 connect to testdb >/dev/null 2>&1 && db2 -x \"<SQL>\""
```
- DBMCFG: `SELECT count(*) FROM SYSIBMADM.DBMCFG` → 113
- DBCFG: `SELECT count(*) FROM SYSIBMADM.DBCFG` → 194
- REG_VARIABLES: `SELECT count(*) FROM SYSIBMADM.REG_VARIABLES` → 3
- Version: `SELECT service_level FROM SYSIBMADM.ENV_INST_INFO` → `DB2 v12.1.4.0`
- Edition: `SELECT installed_prod, license_type FROM SYSIBMADM.ENV_PROD_INFO WHERE license_installed='Y'`
  → `DEC, COMMUNITY`
- Packed version: `SELECT versionnumber FROM SYSIBM.SYSVERSIONS` → `12010400`

---

## 11. Source index

### Live container (authoritative for 12.1.4 column lists + sample values)
- Container `db2-primary`, image `icr.io/db2_community/db2:12.1.4.0`, DB `testdb`, user `db2inst1`.
- Compose: `/home/bits/go/src/github.com/DataDog/dbm/local-dev/db2/docker-compose.yaml`.

### Code (absolute paths)
- Existing Db2 check (connection, version parse, iter_rows, ATTR_CASE):
  `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/ibm_db2.py` (lines 99, 109-125,
  554-578, 567, 610-631)
- Existing Db2 version via driver: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/utils.py:27-28`
- Existing Db2 SQL constants: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/queries.py:15-17`
- Db2 setup/privileges guidance: `/home/bits/dd/integrations-core/ibm_db2/README.md:58-106`
- Postgres settings collector (the pattern to mirror):
  `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/metadata.py:48-61, 206-291`
- Postgres conf `collect_settings`:
  `/home/bits/dd/integrations-core/postgres/datadog_checks/postgres/data/conf.yaml.example:570-587`
- MySQL settings (`mysql_variables`):
  `/home/bits/dd/integrations-core/mysql/datadog_checks/mysql/metadata.py:31, 185`
- SQL Server settings (`sqlserver_configs`):
  `/home/bits/dd/integrations-core/sqlserver/datadog_checks/sqlserver/metadata.py:100-161`
- Metadata payload contract (envelope, identity, kinds):
  `/home/bits/dd/integrations-core/ibm_db2/dev-docs/db2-fidelity-plan/_research/code-dbm-payload-contract.md` (§6)

### Web (IBM official + corroborating)
- DBMCFG view — https://www.ibm.com/docs/en/db2/11.5.x?topic=views-dbmcfg-database-manager-configuration-parameter-information
- DBCFG view + DB_GET_CFG — https://www.ibm.com/docs/en/db2/11.5.x?topic=views-dbcfg-database-configuration-parameter-information
- REG_VARIABLES + LEVEL codes — https://www.databasejournal.com/db2/understanding-ibm-db2-db2set/ ;
  https://datageek.blog/2017/08/22/db2-basics-levels-of-configuration/
- ENV_INST_INFO — https://www.ibm.com/docs/en/db2/11.1.0?topic=views-env-inst-info-current-instance-information
- ENV_* views overview — https://blog.4loeser.net/2014/11/useful-db2-administrative-functions-and.html
- db2level / version detection — https://datageek.blog/2012/06/12/db2-commands-db2level/
- Pending config-change pattern — https://www.dbisoftware.com/blog/db2_performance.php?print=161
- SYSIBMADM authorization model — https://www.ibm.com/docs/en/db2/11.1.0?topic=views-privileges-privilege-information

> NB: IBM 12.1.0 doc URLs (`/docs/en/db2/12.1.0?...`) return HTTP 403 to automated fetch; the 11.5/11.1
> doc pages document the same view schemas, and the **column lists + sample values in §1-§6 above were
> verified directly against the live 12.1.4 container**, so they supersede the docs for version accuracy.
