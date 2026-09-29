#!/bin/sh
# One-shot: join the shard to the cluster, create the monitoring user, and seed a
# sharded, pre-split, indexed collection so state-dependent metrics (chunks.total,
# stats.*, collection.*, index stats, sharded data distribution) have subjects
# before the first scrape. Continuous traffic is activity-gen.sh.
set -eu

log() { echo "seed: $*"; }

log "adding shard01 to the cluster"
mongosh --quiet --host mongos --eval '
  if (!db.getSiblingDB("config").shards.findOne({_id: "shard01"})) {
    sh.addShard("shard01/shard-a:27017");
  }
  print("shards=" + db.getSiblingDB("config").shards.countDocuments({}));'

# The user must exist twice: via mongos it lands on the config servers, which is
# where mongos authenticates, while a direct connection to a shard member
# authenticates against that shard's own admin database.
for host in mongos shard-a; do
  log "creating user ${DB_USERNAME} on ${host}"
  mongosh --quiet --host "$host" --eval '
    const admin = db.getSiblingDB("admin");
    if (!admin.getUser(process.env.DB_USERNAME)) {
      admin.createUser({
        user: process.env.DB_USERNAME,
        pwd: process.env.DB_PASSWORD,
        roles: ["clusterMonitor", "readWriteAnyDatabase"],
      });
    }
    print("user ok");'
done

URI="mongodb://${DB_USERNAME}:${DB_PASSWORD}@mongos:27017/?authSource=admin"

log "seeding activity.orders (sharded, pre-split) and activity.events"
mongosh --quiet "$URI" --eval '
  const act = db.getSiblingDB("activity");
  if (!db.getSiblingDB("config").collections.findOne({_id: "activity.orders"})) {
    sh.shardCollection("activity.orders", {cust_id: 1});
    for (const at of ["c200", "c400", "c600", "c800"]) {
      sh.splitAt("activity.orders", {cust_id: at});
    }
  }
  act.orders.createIndex({status: 1});
  act.orders.createIndex({created: 1});
  act.events.createIndex({kind: 1});
  const docs = [];
  for (let i = 0; i < 1000; i++) {
    docs.push({cust_id: "c" + String(i).padStart(3, "0"), status: i % 2 ? "A" : "D",
               amount: i % 97, created: new Date(), tags: ["x", "y"]});
  }
  act.orders.insertMany(docs);
  act.events.insertMany(docs.map((d) => ({kind: d.status, at: d.created})));
  print("chunks=" + db.getSiblingDB("config").chunks.countDocuments({}));'

# Subjects for the lock contention in activity-gen.sh. Created through mongos so
# both databases are registered, with shard01 as primary, before activity-gen
# touches them directly on shard-a.
log "seeding lockdrill (hot documents, capped collection) and lockdrill_aux"
mongosh --quiet "$URI" --eval '
  const drill = db.getSiblingDB("lockdrill");
  for (const id of [1, 2]) {
    drill.hot.updateOne({_id: id}, {$setOnInsert: {n: 0}}, {upsert: true});
  }
  if (!drill.getCollectionNames().includes("capped")) {
    drill.createCollection("capped", {capped: true, size: 1048576});
  }
  db.getSiblingDB("lockdrill_aux").t.insertOne({at: new Date()});
  print("lockdrill ok");'

log "seed complete"
