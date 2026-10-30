#!/bin/sh
# Drives oracle-full so the oracle check reports its V$SYSMETRIC surface with
# non-zero values (an idle instance reports zero for most per-second metrics).
# Starts a long-lived lock/temp holder session, then loops the workload. Consumes
# DB_HOST/DB_PORT/ORACLE_PASSWORD from the fixture; the ddapp schema comes from
# ../seed.sh.
set -eu

DB_PORT="${DB_PORT:-1521}"
APP="ddapp/${ORACLE_PASSWORD}@//${DB_HOST}:${DB_PORT}/FREEPDB1"
SYS="sys/${ORACLE_PASSWORD}@//${DB_HOST}:${DB_PORT}/FREE as sysdba"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent oracle-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# Runs the SQL on stdin in a fresh session (each call is also a logon).
app() { sqlplus -L -s "$APP" > /dev/null 2>&1 || true; }
sys() { sqlplus -L -s "$SYS" > /dev/null 2>&1 || true; }

# Long-lived holder session, restarted if it drops:
#   - ~20 MB of session-private rows in a global temporary table -> temp_space_used;
#   - an uncommitted update of lock_rows id=1, so readers apply undo
#     (consistent_read_changes) and `for update wait 1` times out (enqueue_timeouts).
hold() {
  while :; do
    {
      echo "set feedback off"
      echo "insert into temp_hold select level, 'held' from dual connect by level <= 20000;"
      echo "commit;"
      echo "update lock_rows set v = v + 1 where id = 1;"
      while :; do echo "select count(*) from temp_hold;"; sleep 20; done
    } | sqlplus -L -s "$APP" > /dev/null 2>&1 || true
    sleep 5
  done
}

# Two sessions take lock_rows id=2/id=3 in opposite order: one gets ORA-00060
# (enqueue_deadlocks), rolls back, and the other completes.
deadlock() {
  printf 'update lock_rows set v = v + 1 where id = 2;\nexec dbms_session.sleep(2)\nupdate lock_rows set v = v + 1 where id = 3;\nrollback;\nexit\n' | app &
  p1=$!
  printf 'update lock_rows set v = v + 1 where id = 3;\nexec dbms_session.sleep(2)\nupdate lock_rows set v = v + 1 where id = 2;\nrollback;\nexit\n' | app &
  p2=$!
  wait "$p1" "$p2" || true
}

log "starting lock/temp holder session"
hold &
holder=$!

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  # dbwr_checkpoints every iteration; every 5th iteration also flush the buffer
  # cache so the index lookups below do single-block physical reads
  # (physical_reads, avg_synchronous_single_block_read_latency).
  if [ $(( i % 5 )) -eq 1 ]; then
    printf 'alter system checkpoint;\nalter system flush buffer_cache;\nexit\n' | sys
  else
    printf 'alter system checkpoint;\nexit\n' | sys
  fi

  # Bound table growth: truncating keeps the indexes small enough to keep splitting.
  if [ $(( i % 100 )) -eq 0 ]; then
    printf 'truncate table split_keys;\ntruncate table orders;\nexit\n' | app
  fi

  deadlock &
  dl=$!

  app <<'SQL'
set feedback off heading off
declare
  n number;
  s varchar2(4000);
begin
  -- user_commits, redo_generated/redo_writes, db_block_changes/gets
  for i in 1 .. 2000 loop
    insert into orders values (orders_seq.nextval, trunc(dbms_random.value(1, 1000)),
      round(dbms_random.value(1, 500), 2), 'NEW', rpad('note', 100, 'x'));
    if mod(i, 20) = 0 then commit; end if;
  end loop;
  commit;
  -- user_rollbacks
  for i in 1 .. 20 loop
    update orders set status = 'HOLD' where customer_id = i;
    rollback;
  end loop;
  -- soft parses, execute_without_parse, logical/consistent reads, index lookups
  for i in 1 .. 500 loop
    select count(*) into n from orders where customer_id = i;
  end loop;
  -- hard_parses: distinct literal statements
  for i in 1 .. 200 loop
    execute immediate 'select count(*) from orders where customer_id = '
      || trunc(dbms_random.value(1, 1e9)) into n;
  end loop;
  -- parse_failures
  for i in 1 .. 20 loop
    begin
      execute immediate 'select count(*) from missing_table_' || i into n;
    exception
      when others then null;
    end;
  end loop;
  -- leaf_nodes_splits / branch_node_splits: wide keys that only differ in their
  -- last 20 characters, so the suffix-truncated branch entries stay wide too
  insert into split_keys select rpad('k', 360, 'k') || dbms_random.string('x', 20)
    from dual connect by level <= 3000;
  commit;
  -- physical_writes_direct_lobs / physical_reads_direct_lobs: NOCACHE out-of-row LOBs
  for i in 1 .. 20 loop
    insert into lob_docs values (1000 + i, to_clob(rpad('lob', 4000, 'x')) || rpad('z', 4000, 'z'));
  end loop;
  commit;
  for r in (select body from lob_docs where id <= 50) loop
    s := dbms_lob.substr(r.body, 4000, 4001);
  end loop;
  delete from lob_docs where id > 1000;
  commit;
  -- consistent_read_changes: lock_rows id=1 carries the holder's uncommitted change
  for i in 1 .. 200 loop
    select sum(v) into n from lock_rows;
  end loop;
  -- enqueue_timeouts: the holder owns id=1, so this waits 1s and fails (ORA-30006)
  begin
    select v into n from lock_rows where id = 1 for update wait 1;
  exception
    when others then null;
  end;
  rollback;
end;
/
-- long_table_scans, physical_reads_direct: full scan above the small-table threshold
select /*+ full(b) */ count(*) from big_scan b where pad like 'zz%';
-- disk_sorts, temp direct I/O (physical_writes_direct): a ~20 MB ORDER BY with a
-- 1 MB work area spills to temp in one pass
alter session set workarea_size_policy = manual;
alter session set sort_area_size = 1048576;
declare
  n number;
begin
  for r in (select id from big_scan where id <= 20000 order by pad desc, id) loop
    n := r.id;
  end loop;
end;
/
alter session set workarea_size_policy = auto;
-- memory sorts (memory_sorts_ratio, rows_per_sort, sorts_per_user_call)
select max(amount) from (select amount from orders where rownum <= 5000 order by amount);
exit
SQL

  wait "$dl" || true

  if [ $(( i % 10 )) -eq 0 ]; then log "iteration $i"; fi

  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

kill "$holder" 2> /dev/null || true
log "PASS: activity workload complete after $i iterations"
