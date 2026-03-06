# SDBM-2431: Test MongoDB aggregate explain cursor fix

Verify that the Mongo integration can run explain on aggregate commands that lack `cursor: {}` (required by the explain command wrapper form on all MongoDB versions 6+).

## 1. Spin up MongoDB 7 (from integrations-core root)

```bash
docker compose -f docker-compose-mongo7-test.yaml up -d
```

## 2. Seed data and verify explain behavior (mongosh)

Connect and run:

```javascript
// mongosh mongodb://localhost:27017

use testdb

db.products.insertMany([
  { name: "Widget", price: 9.99, category: "gadgets", stock: 100 },
  { name: "Gizmo", price: 19.99, category: "gadgets", stock: 50 },
  { name: "Doohickey", price: 4.99, category: "tools", stock: 200 },
  { name: "Thingamajig", price: 29.99, category: "tools", stock: 25 },
])
db.products.createIndex({ category: 1, price: -1 })

// find explain works without cursor (cursor is NOT accepted by find)
db.runCommand({ explain: { find: "products", filter: { category: "gadgets" } }, verbosity: "queryPlanner" })

// Aggregate WITHOUT cursor: FAILS with "The 'cursor' option is required..."
db.runCommand({ explain: { aggregate: "products", pipeline: [{ $match: { category: "gadgets" } }] }, verbosity: "queryPlanner" })

// Aggregate WITH cursor (fix): succeeds
db.runCommand({ explain: { aggregate: "products", pipeline: [{ $match: { category: "gadgets" } }], cursor: {} }, verbosity: "queryPlanner" })
```

**Note:** Only `aggregate` requires `cursor: {}` in the explain command wrapper form. Other commands (`find`, `count`, `distinct`, `findAndModify`) reject `cursor` as an unknown BSON field. This behavior is consistent across MongoDB 6.0, 7.0, and 8.0. Most aggregates captured from `$currentOp` already include `cursor: {}` (added by PyMongo), but some may lack it (older drivers, manual `runCommand`, mongos forwarding).

## 3. Sustained workload (optional, for $currentOp sampling)

In a separate terminal:

```bash
mongosh mongodb://localhost:27017 --eval '
while(true) {
  db = db.getSiblingDB("testdb");
  db.products.find({ category: "gadgets" }).toArray();
  db.products.find({ price: { $gt: 10 } }).sort({ price: -1 }).toArray();
  db.products.distinct("category");
  db.products.aggregate([{ $group: { _id: "$category", avgPrice: { $avg: "$price" } } }]).toArray();
  db.products.countDocuments({ stock: { $lt: 50 } });
  sleep(500);
}
'
```

## 4. E2E (ddev env)

From integrations-core, on branch `pierreln-dd/sdbm-2431-mongo7-explain-cursor`:

**Ensure port 27017 is free** (stop any manual Mongo compose first: `docker compose -f docker-compose-mongo7-test.yaml down -v`).

```bash
ddev env show mongo
ddev env start --dev mongo py3.13-7.0-standalone
ddev env test --dev mongo py3.13-7.0-standalone
ddev env stop mongo py3.13-7.0-standalone
```

(If `py3.13-7.0-standalone` is not listed, use the environment name shown by `ddev env show mongo`.)

## 5. What to verify

- **Before fix (master):** Aggregate explain without `cursor` fails with FailedToParse / "The 'cursor' option is required" in `collection_errors`.
- **After fix (branch):** Aggregate explain succeeds because `cursor: {}` is automatically added when missing.
- Check integration logs: `ddev env agent mongo py3.13-7.0-standalone log` for explain-related errors.

## 6. Cleanup

```bash
docker compose -f docker-compose-mongo7-test.yaml down -v
```

Optionally remove the compose file: `rm docker-compose-mongo7-test.yaml`.
