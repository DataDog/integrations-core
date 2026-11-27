#!/bin/bash
# One-shot seed for oracle-full. Creates the Datadog monitoring user (with the
# grants and the `dd_session` view the check needs under `dbm: true`) in the CDB
# root, and the `ddapp` workload schema in FREEPDB1 that ../activity-gen.sh drives.
# Idempotent. Consumes DB_HOST/ORACLE_PASSWORD/DB_USERNAME/DB_PASSWORD.
set -eu

DB_PORT="${DB_PORT:-1521}"
ROOT="//${DB_HOST}:${DB_PORT}/FREE"
PDB="//${DB_HOST}:${DB_PORT}/FREEPDB1"

log() { echo "seed: $*"; }

sys() {
  {
    echo "whenever sqlerror exit failure"
    echo "set define '&' verify off feedback off serveroutput on"
    echo "define dd_user = ${DB_USERNAME}"
    echo "define dd_password = ${DB_PASSWORD}"
    echo "define app_password = ${ORACLE_PASSWORD}"
    cat
    echo "exit"
  } | sqlplus -L -s "sys/${ORACLE_PASSWORD}@${ROOT} as sysdba"
}

log "creating ${DB_USERNAME} and grants"
sys <<'SQL'
declare
  n number;
begin
  select count(*) into n from dba_users where username = upper('&dd_user');
  if n = 0 then
    execute immediate 'create user &dd_user identified by "&dd_password" container=all';
  else
    execute immediate 'alter user &dd_user identified by "&dd_password" container=all';
  end if;
  execute immediate 'alter user &dd_user set container_data=all container=current';
end;
/
grant create session to &dd_user container=all;

-- Mirrors the Agent's sql/user/grants.sql for a self-managed CDB.
declare
  type array_t is table of varchar2(64);
  objs array_t := array_t(
    'v_$session', 'v_$database', 'v_$containers', 'v_$sqlstats', 'v_$instance',
    'dba_feature_usage_statistics', 'v_$sql_plan_statistics_all', 'v_$process',
    'v_$con_sysmetric', 'cdb_tablespace_usage_metrics', 'cdb_tablespaces',
    'v_$sqlcommand', 'v_$datafile', 'v_$sysmetric', 'v_$sgainfo', 'v_$pdbs',
    'cdb_services', 'v_$osstat', 'v_$parameter', 'v_$sql', 'v_$pgastat',
    'v_$asm_diskgroup', 'v_$rsrcmgrmetric', 'v_$dataguard_config',
    'v_$dataguard_stats', 'v_$transaction', 'v_$locked_object',
    'v_$active_session_history', 'v_$lock', 'gv_$lock', 'dba_objects',
    'cdb_data_files', 'dba_data_files'
  );
begin
  for i in 1 .. objs.count loop
    begin
      execute immediate 'grant select on ' || objs(i) || ' to &dd_user';
    exception
      when others then
        dbms_output.put_line('skipped grant on ' || objs(i) || ': ' || sqlerrm);
    end;
  end loop;
end;
/

-- Session view for DBM query samples, as in the Agent's create_activity_view.sql.
create or replace view dd_session as
select /*+ push_pred(sq) push_pred(sq_prev) */
  s.indx as sid,
  s.ksuseser as serial#,
  s.ksuudlna as username,
  decode(bitand(s.ksuseidl, 9), 1, 'ACTIVE', 0, decode(bitand(s.ksuseflg, 4096), 0, 'INACTIVE', 'CACHED'), 'KILLED') as status,
  s.ksuseunm as osuser,
  s.ksusepid as process,
  s.ksusemnm as machine,
  s.ksusemnp as port,
  s.ksusepnm as program,
  decode(bitand(s.ksuseflg, 19), 17, 'BACKGROUND', 1, 'USER', 2, 'RECURSIVE', '?') as type,
  s.ksusesqi as sql_id,
  sq.force_matching_signature as force_matching_signature,
  s.ksusesph as sql_plan_hash_value,
  s.ksusesesta as sql_exec_start,
  s.ksusesql as sql_address,
  case when bitand(s.ksusstmbv, power(2, 04)) = power(2, 04) then 'Y' else 'N' end as in_parse,
  case when bitand(s.ksusstmbv, power(2, 07)) = power(2, 07) then 'Y' else 'N' end as in_hard_parse,
  s.ksusepsi as prev_sql_id,
  s.ksusepha as prev_sql_plan_hash_value,
  s.ksusepesta as prev_sql_exec_start,
  sq_prev.force_matching_signature as prev_force_matching_signature,
  s.ksusepsq as prev_sql_address,
  s.ksuseapp as module,
  s.ksuseact as action,
  s.ksusecli as client_info,
  s.ksuseltm as logon_time,
  s.ksuseclid as client_identifier,
  s.ksusstmbv as op_flags,
  decode(s.ksuseblocker,
    4294967295, 'UNKNOWN', 4294967294, 'UNKNOWN', 4294967293, 'UNKNOWN', 4294967292, 'NO HOLDER', 4294967291, 'NOT IN WAIT',
    'VALID') as blocking_session_status,
  decode(s.ksuseblocker,
    4294967295, to_number(null), 4294967294, to_number(null), 4294967293, to_number(null),
    4294967292, to_number(null), 4294967291, to_number(null), bitand(s.ksuseblocker, 2147418112) / 65536) as blocking_instance,
  decode(s.ksuseblocker,
    4294967295, to_number(null), 4294967294, to_number(null), 4294967293, to_number(null),
    4294967292, to_number(null), 4294967291, to_number(null), bitand(s.ksuseblocker, 65535)) as blocking_session,
  decode(s.ksusefblocker,
    4294967295, 'UNKNOWN', 4294967294, 'UNKNOWN', 4294967293, 'UNKNOWN', 4294967292, 'NO HOLDER', 4294967291, 'NOT IN WAIT',
    'VALID') as final_blocking_session_status,
  decode(s.ksusefblocker,
    4294967295, to_number(null), 4294967294, to_number(null), 4294967293, to_number(null), 4294967292, to_number(null),
    4294967291, to_number(null), bitand(s.ksusefblocker, 2147418112) / 65536) as final_blocking_instance,
  decode(s.ksusefblocker,
    4294967295, to_number(null), 4294967294, to_number(null), 4294967293, to_number(null), 4294967292, to_number(null),
    4294967291, to_number(null), bitand(s.ksusefblocker, 65535)) as final_blocking_session,
  decode(w.kslwtinwait,
    1, 'WAITING', decode(bitand(w.kslwtflags, 256), 0, 'WAITED UNKNOWN TIME',
    decode(round(w.kslwtstime / 10000), 0, 'WAITED SHORT TIME', 'WAITED KNOWN TIME'))) as state,
  e.kslednam as event,
  e.ksledclass as wait_class,
  w.kslwtstime as wait_time_micro,
  c.name as pdb_name,
  sq.sql_text as sql_text,
  sq.sql_fulltext as sql_fulltext,
  sq_prev.sql_fulltext as prev_sql_fulltext,
  comm.command_name
from
  x$ksuse s,
  x$kslwt w,
  x$ksled e,
  v$sql sq,
  v$sql sq_prev,
  v$containers c,
  v$sqlcommand comm
where
  bitand(s.ksspaflg, 1) != 0
  and bitand(s.ksuseflg, 1) != 0
  and s.inst_id = userenv('Instance')
  and s.indx = w.kslwtsid
  and w.kslwtevt = e.indx
  and s.ksusesqi = sq.sql_id(+)
  and decode(s.ksusesch, 65535, to_number(null), s.ksusesch) = sq.child_number(+)
  and s.ksusepsi = sq_prev.sql_id(+)
  and decode(s.ksusepch, 65535, to_number(null), s.ksusepch) = sq_prev.child_number(+)
  and s.con_id = c.con_id(+)
  and s.ksuudoct = comm.command_type(+);
grant select on dd_session to &dd_user;
SQL

log "creating the ddapp workload schema in FREEPDB1"
sys <<'SQL'
alter session set container = FREEPDB1;
declare
  n number;
begin
  select count(*) into n from dba_users where username = 'DDAPP';
  if n = 0 then
    execute immediate 'create user ddapp identified by "&app_password" quota unlimited on users default tablespace users';
  else
    execute immediate 'alter user ddapp identified by "&app_password"';
  end if;
end;
/
grant create session, create table, create sequence, create procedure to ddapp;

alter session set current_schema = ddapp;
declare
  procedure ddl(stmt varchar2) is
  begin
    execute immediate stmt;
  exception
    -- ORA-00955: name is already used by an existing object
    when others then if sqlcode != -955 then raise; end if;
  end;
begin
  -- OLTP table: commits, rollbacks, redo, block changes, single-block reads.
  ddl('create table orders (id number primary key, customer_id number, amount number, status varchar2(20), note varchar2(200))');
  ddl('create index orders_customer_ix on orders (customer_id)');
  ddl('create sequence orders_seq cache 1000');
  -- Larger than the small-table threshold: long table scans, serial direct-path reads, disk sorts.
  ddl('create table big_scan (id number, pad char(1000)) nologging');
  -- Out-of-row NOCACHE LOBs: direct LOB reads and writes.
  ddl('create table lob_docs (id number, body clob) lob (body) store as (disable storage in row nocache)');
  -- Wide random keys so leaf (and periodically branch) index blocks split.
  ddl('create table split_keys (k varchar2(400))');
  ddl('create index split_keys_ix on split_keys (k)');
  -- Rows contended by the lock-holder, timeout and deadlock sessions.
  ddl('create table lock_rows (id number primary key, v number)');
  -- Session-private rows held in temp for the lifetime of the holder session.
  ddl('create global temporary table temp_hold (id number, pad char(1000)) on commit preserve rows');
end;
/
insert into lock_rows select level, 0 from dual
  where not exists (select 1 from lock_rows) connect by level <= 10;
insert /*+ append */ into big_scan select level, 'row' || level from dual
  where not exists (select 1 from big_scan) connect by level <= 200000;
commit;
insert into lob_docs select level, to_clob(rpad('lob', 4000, 'x')) || rpad('y', 4000, 'y') from dual
  where not exists (select 1 from lob_docs) connect by level <= 200;
commit;
begin
  dbms_stats.gather_schema_stats('DDAPP');
end;
/
SQL

log "verifying ${DB_USERNAME} can log in and read V\$SYSMETRIC"
printf 'whenever sqlerror exit failure\nset heading off feedback off\nselect count(*) from v$sysmetric;\nexit\n' \
  | sqlplus -L -s "${DB_USERNAME}/${DB_PASSWORD}@${ROOT}"
printf 'whenever sqlerror exit failure\nset heading off feedback off\nselect count(*) from big_scan;\nexit\n' \
  | sqlplus -L -s "ddapp/${ORACLE_PASSWORD}@${PDB}"
log "seed-done"
