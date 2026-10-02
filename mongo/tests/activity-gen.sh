#!/bin/sh
# Drives mongo-full so the mongo check and the OTel mongodbreceiver report their
# rate/counter metrics with non-zero values (an idle mongod reports zero for
# most of them). Each iteration is one mongosh session through mongos, so the
# connection and session counters churn too. Writes replicate to the delayed
# secondary, which keeps opcountersrepl and the repl.* counters moving.
# Consumes DB_HOST/DB_PORT/DB_USERNAME/DB_PASSWORD and DB_SHARD_HOST from the
# fixture.
set -eu

URI="mongodb://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-27017}/activity?authSource=admin"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever
LOCK_DRILL="${LOCK_DRILL:-1}"

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent mongo-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# sessions.count reads config.system.sessions, which only holds sessions still
# open at a refresh; each iteration below ends its session on exit, so keep one
# long-lived session active in the background for the task's lifetime.
log "opening long-lived session"
while :; do
  mongosh --quiet "$URI" --eval '
    const s = db.getMongo().startSession();
    while (true) { s.getDatabase("activity").events.findOne(); sleep(5000); }
  ' || true
  sleep 5
done &

# Lock contention. serverStatus only reports locks.<type>.acquireWaitCount and
# timeAcquiringMicros once an acquisition has waited on a conflicting mode, and
# the one-at-a-time traffic below never conflicts. A slow writer holds intent
# locks (IX) on lockdrill.hot almost continuously, two fast writers and a dbStats
# keep more intent requests (IS/IX) arriving, and two holders periodically
# request conflicting modes, so the holders wait on the slow writer and the fast
# requests queue behind the holders:
#   - createIndexes (S for the drain, X to commit) and dropIndexes (X): Collection;
#   - dbHash (S) and a cross-database renameCollection (X on the target): Database;
#   - fsync lock (S) and setUserWriteBlockMode (X): Global. These two are the
#     lock drill: setUserWriteBlockMode blocks every user write cluster-wide for
#     its window, so LOCK_DRILL=0 skips both and keeps the rest running.
# Writes to the capped collection take the Metadata lock in X mode. dbHash,
# fsync, and the cross-database rename are mongod-only, so they and the writers
# run directly on the shard primary (where the waits are counted); the cluster
# commands run through mongos. Every lock held beyond its command is released in
# a finally, and each holder first clears one a killed predecessor left behind.
SHARD_URI="mongodb://${DB_USERNAME}:${DB_PASSWORD}@${DB_SHARD_HOST}:${DB_SHARD_PORT:-27017}/lockdrill?authSource=admin&directConnection=true"
MONGOS_LOCK_URI="mongodb://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-27017}/lockdrill?authSource=admin"

# fsync lock and the write block outlive the session that took them, so release
# both if the script stops mid-window. The holders are killed first so none
# re-takes a lock after the release.
release_locks() {
  trap '' TERM
  kill -TERM 0 2>/dev/null || :
  trap - TERM
  # fsync first: setUserWriteBlockMode waits behind a held fsync lock.
  timeout -k 1 4 mongosh --quiet "$SHARD_URI" --eval '
    try { while (db.adminCommand({fsyncUnlock: 1}).ok) {} }
    catch (e) { if (e.codeName !== "IllegalOperation") throw e; }' >/dev/null ||
    log "releasing the fsync lock failed"
  timeout -k 1 4 mongosh --quiet "$MONGOS_LOCK_URI" --eval '
    db.adminCommand({setUserWriteBlockMode: 1, global: false})' >/dev/null ||
    log "releasing setUserWriteBlockMode failed"
  log "lock drill released"
}
if [ "$LOCK_DRILL" = "0" ]; then
  log "lock drill disabled via LOCK_DRILL=0"
else
  trap release_locks EXIT
  trap 'exit 1' INT TERM HUP
fi

log "starting lock contention"
# The $where runs in a single plan step, which does not yield, so each update
# holds its locks for the ~100 ms sleep. It targets its own document: sharing
# one with the fast writers turns the sleep into write-conflict retries.
while :; do
  mongosh --quiet "$SHARD_URI" --eval '
    while (true) {
      try {
        db.hot.updateOne({_id: 2, $where: "sleep(100); return true;"}, {$inc: {n: 1}});
      } catch (e) {
        if (e.codeName !== "UserWritesBlocked") throw e;
      }
    }' || log "slow lock writer failed; restarting"
  sleep 5
done &

for w in 1 2; do
  while :; do
    mongosh --quiet "$SHARD_URI" --eval '
      while (true) {
        try {
          db.hot.updateOne({_id: 1}, {$inc: {n: 1}});
          db.hot.findOne({_id: 1});
          db.runCommand({dbStats: 1});
        } catch (e) {
          // Expected while setUserWriteBlockMode briefly blocks writes.
          if (e.codeName !== "UserWritesBlocked") throw e;
        }
        sleep(1);
      }' || log "lock writer $w failed; restarting"
    sleep 5
  done &
done

while :; do
  LOCK_DRILL="$LOCK_DRILL" mongosh --quiet "$SHARD_URI" --eval '
    const drill = process.env.LOCK_DRILL !== "0";
    const admin = db.getSiblingDB("admin");
    const unlock = () => {
      try { admin.runCommand({fsyncUnlock: 1}); return true; }
      catch (e) { if (e.codeName === "IllegalOperation") return false; throw e; }
    };
    while (unlock()) {}
    while (true) {
      db.hot.createIndex({n: 1});
      db.hot.dropIndex({n: 1});
      db.runCommand({dbHash: 1});
      db.getSiblingDB("lockdrill_aux").t.insertOne({at: new Date()});
      admin.runCommand({renameCollection: "lockdrill_aux.t", to: "lockdrill.renamed", dropTarget: true});
      if (drill) {
        admin.runCommand({fsync: 1, lock: true});
        try { sleep(100); } finally { unlock(); }
      }
      sleep(3000);
    }' || log "shard lock holder failed; restarting"
  sleep 5
done &

while :; do
  LOCK_DRILL="$LOCK_DRILL" mongosh --quiet "$MONGOS_LOCK_URI" --eval '
    const drill = process.env.LOCK_DRILL !== "0";
    const admin = db.getSiblingDB("admin");
    const unblock = () => admin.runCommand({setUserWriteBlockMode: 1, global: false});
    unblock();
    while (true) {
      db.capped.insertOne({at: new Date()});
      if (drill) {
        try { admin.runCommand({setUserWriteBlockMode: 1, global: true}); } finally { unblock(); }
      }
      sleep(3000);
    }' || log "mongos lock holder failed; restarting"
  sleep 5
done &

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

# evalya ignores compose restart policies, so a failed iteration must not end the
# loop (set -e would otherwise stop the workload for the rest of the run).
while :; do
  i=$(( i + 1 ))
  # Wrapped in a function so mongosh does not print each result. Run in the
  # background and waited on, so a stop signal reaches the trap even while the
  # iteration is stuck behind a held lock (sh defers traps until a foreground
  # command returns).
  ITER="$i" mongosh --quiet "$URI" --eval '(() => {
    const i = Number(process.env.ITER);
    const cust = () => "c" + String(Math.floor(Math.random() * 1000)).padStart(3, "0");

    // opcounters.insert, metrics.document.inserted, oplatencies.writes
    const docs = [];
    for (let j = 0; j < 50; j++) {
      docs.push({cust_id: cust(), status: j % 3 ? "A" : "D", amount: j, created: new Date(),
                 pad: "x".repeat(512)});
    }
    db.orders.insertMany(docs);
    db.events.insertOne({kind: "tick", i: i, at: new Date()});

    // opcounters.query + index accesses (indexed) and a collection scan.
    db.orders.find({status: "A"}).limit(20).toArray();
    db.orders.find({cust_id: cust()}).toArray();
    db.events.find({i: {$gt: i - 5}}).toArray();

    // opcounters.getmore: small batches force getMore round trips.
    db.orders.find({created: {$gt: new Date(Date.now() - 60000)}}).batchSize(10).limit(200).toArray();

    // opcounters.update / metrics.document.updated
    db.orders.updateMany({cust_id: cust()}, {$inc: {amount: 1}, $set: {status: "U"}});
    db.orders.updateOne({status: "A"}, {$set: {touched: new Date()}});

    // opcounters.command + oplatencies.commands
    db.orders.aggregate([{$match: {status: "A"}}, {$group: {_id: "$status", n: {$sum: 1}}}]).toArray();
    db.orders.countDocuments({status: "D"});
    db.runCommand({dbStats: 1});
    // listIndexes counts as a collection command (collection.commands.opsps).
    db.orders.getIndexes();
    db.events.getIndexes();

    // DDL replicates as a command, so opcountersrepl.command moves on shard-b.
    if (i % 10 === 0) { db.churn.drop(); db.createCollection("churn"); }

    // opcounters.delete / metrics.document.deleted, keeping the data set bounded.
    db.orders.deleteMany({created: {$lt: new Date(Date.now() - 120000)}});
    db.events.deleteMany({at: {$lt: new Date(Date.now() - 120000)}});
  })()' &
  wait $! || log "iteration $i failed; continuing"

  [ $(( i % 20 )) -eq 0 ] && log "iteration $i"
  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
