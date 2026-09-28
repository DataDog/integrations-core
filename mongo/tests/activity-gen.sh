#!/bin/sh
# Drives mongo-full so the mongo check and the OTel mongodbreceiver report their
# rate/counter metrics with non-zero values (an idle mongod reports zero for
# most of them). Each iteration is one mongosh session through mongos, so the
# connection and session counters churn too. Writes replicate to the delayed
# secondary, which keeps opcountersrepl and the repl.* counters moving.
# Consumes DB_HOST/DB_PORT/DB_USERNAME/DB_PASSWORD from the fixture.
set -eu

URI="mongodb://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-27017}/activity?authSource=admin"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

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

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

# evalya ignores compose restart policies, so a failed iteration must not end the
# loop (set -e would otherwise stop the workload for the rest of the run).
while :; do
  i=$(( i + 1 ))
  # Wrapped in a function so mongosh does not print each result.
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
  })()' || log "iteration $i failed; continuing"

  [ $(( i % 20 )) -eq 0 ] && log "iteration $i"
  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
