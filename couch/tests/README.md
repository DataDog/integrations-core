# couch test fixtures

The pytest suite plus the Compose environments used by the tests and by the
evalya fixture in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/compose_v1.yaml` | Single CouchDB 1.x server, used by the pytest suite for 1.x. |
| `compose/compose_v2.yaml` | Three-node CouchDB 2.x/3.x cluster, used by the pytest suite for 2.x and later. |
| `compose/full-coverage.compose` | Full metric-coverage environment, published as the `couch-full` evalya task. |

## The couch-full fixture

`couch-full` makes the couch check emit every metric used by the integration's
two OOTB dashboards with non-zero values. The dashboards read different metric
names: the check selects its `CouchDB2` code path for 2.x and later
(CouchDB-overview: `couchdb.couchdb.*`, `couchdb.by_db.file_size`) and its
`CouchDB1` code path for 1.x (CouchDBv1-overview: `couchdb.httpd*`,
`couchdb.by_db.disk_size`). No single server emits both, so the fixture runs one
of each. It has five services:

- **couchdb**: CouchDB 3.x, single node, with an admin account.
- **couchdb-v1**: CouchDB 1.x in admin party mode (no admins), like the pytest
  1.x environment. The image is amd64-only and runs under emulation on other
  hosts. Its stock entrypoint drops privileges with a `gosu` build that crashes
  under qemu, so the service does the same step with `su`.
- **seed**: one-shot. Creates the system databases on 3.x, a `kennel` database
  with 50 documents and a design document on both servers, and a non-admin
  `_users` account (`ddreader`). The design document's `validate_doc_update`
  rejects documents flagged `forbidden`, which gives both servers a 403 path.
- **activity-gen**: continuous workload (`activity-gen.sh`) against both
  servers. Each iteration makes GET, PUT, POST and DELETE requests, a
  `_bulk_docs` request, and a view read. It also triggers each status code on
  the dashboards (200, 201, 400, 401, 403, 404, 405, 409, 412) and authenticates
  as `ddreader` to produce auth cache hits. Each failed login uses a new unknown
  user name, which produces a 401 and an auth cache miss. CouchDB 3.x locks out a
  user (403) after repeated failed logins from one client, so the workload never
  sends a wrong password for a real account.
- **gateway**: the entrypoint, an nginx TCP passthrough that only forwards
  traffic. Port 5984 reaches the 3.x server and port 5985 reaches the 1.x server.
  Nothing is rewritten or injected. No host port is published; consumers reach
  it over the managed network through the `DB_HOST` label.

Configure the check with one instance per port:

```yaml
instances:
  - server: http://<DB_HOST>:<DB_PORT>       # 3.x
    user: <DB_USERNAME>
    password: <DB_PASSWORD>
  - server: http://<DB_HOST>:<DB_V1_PORT>    # 1.x, no credentials
```

### Inputs

Each input has a working default, so the task runs unattended. Set any of them
in the host environment before starting the fixture to override it.

| Variable | Default | Effect |
|---|---|---|
| `COUCH_VERSION` | `3.4` | Image tag of the 2.x/3.x server. The seed and activity-gen use the same image. |
| `COUCH_V1_VERSION` | `1.6.1` | Image tag of the 1.x server. |
| `DB_USERNAME` | `dduser` | Admin user on the 3.x server, published as `provides.DB_USERNAME`. |
| `DB_PASSWORD` | `pawprint` | Admin password on the 3.x server, published as `provides.DB_PASSWORD`. |
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture. The workload container stays up but sends no traffic. |
| `ACTIVITY_DURATION` | `0` | Stop the workload after this many seconds. `0` runs it forever. |
| `NGINX_VERSION` | `1.27-alpine` | Image tag of the gateway. |

```shell
evalya run --path couch/tests/evalya.yaml --task couch-full
ACTIVITY_GEN=0 evalya run --path couch/tests/evalya.yaml --task couch-full
```
