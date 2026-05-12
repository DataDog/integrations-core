# Environment Setup Automation Design

**Date:** 2026-05-05  
**Last revised:** 2026-05-12  
**Status:** Draft  
**Scope:** `ddev lab` — agentic framework for provisioning, seeding, and load-testing Datadog integration environments on remote cloud infrastructure (AWS and GCP)

---

## 1. Problem and Goals

Setting up environments for Datadog integrations is one of the highest-friction steps in integration development. The pain concentrates in three areas:

1. **Infrastructure complexity** — Some integrations (Oracle DB, IBM MQ, Kafka + ZooKeeper, Lustre clusters) require real VMs, licenses, or multi-node topologies that cannot run locally and require significant manual effort.
2. **Data quality** — Test datasets are minimal or absent; developers run checks against empty systems that don't reflect production behavior, masking metric collection gaps.
3. **Portability** — Environment setup knowledge is tribal. When a developer leaves or switches integrations, the environment has to be reconstructed from scratch.

### Goals

| Priority | Goal |
|----------|------|
| Primary | Provision a fully running integration environment on remote cloud infrastructure with a single command |
| Primary | Seed the environment with realistic-looking data |
| Primary | Generate continuous background load that exercises the integration's metric surface |
| Primary | Include a configured Datadog Agent in every lab, ready to run the integration check |
| Optional | Produce a human-readable record of what was set up and why |

### Non-goals

- Replacing `ddev env` for local unit/integration testing — `ddev lab` is for E2E and exploratory work against live infrastructure
- Supporting every integration on day one — start with the hardest ones (Oracle, IBM MQ, Kafka, Cassandra, Lustre)
- Running any part of the environment on a developer's local machine — all labs are remote

---

## 2. Architecture Overview

The system has two distinct layers:

```
┌──────────────────────────────────────────────────────────────────┐
│  AI Research Phase  (runs once per integration version)          │
│                                                                  │
│  Sources: vendor docs, Docker Hub, metadata.csv, manifest.json   │
│  (Does NOT require existing tests or compose files)              │
│                                                                  │
│  Produces complete tests/lab/ subtree:                           │
│    lab.yaml                  ← machine-readable manifest         │
│    tests/lab/RESEARCH.md     ← human-readable narrative          │
│    tests/lab/compose/        ← service topology (Docker)         │
│    tests/lab/seed/           ← numbered, idempotent scripts      │
│    tests/lab/load/           ← Locust or k6 script               │
│    tests/lab/agent/          ← Datadog Agent integration config  │
│    tests/lab/provision/      ← Ansible playbook (bare-metal only)│
│    [starter Pulumi program]  ← reviewed + merged to infra/       │
└────────────────────────┬─────────────────────────────────────────┘
                         │  artifacts reviewed + committed
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  Deterministic Execution Layer  (ddev lab CLI)                   │
│                                                                  │
│  create:   pulumi up → wait SSH → healthchecks →                 │
│            seed → load → start Agent → register                  │
│                                                                  │
│  stop:     stop load → docker compose down → update registry     │
│                                                                  │
│  destroy:  stop load → stop services → pulumi destroy →          │
│            deregister                                            │
└──────────────────────────────────────────────────────────────────┘
```

No AI runs at execution time. The AI phase is a one-time investment per integration version, repeatable when the technology version changes. The execution layer is a simple deterministic pipeline any team member can run.

---

## 3. The Research Phase

### Trigger

```bash
ddev lab research <integration>                          # generate all artifacts fresh
ddev lab research --update <integration> --version 3.8  # update for a new tech version
```

### Information sources

The research agent has access to the following — **and nothing else**. The integration may be brand new with no existing tests or compose files, so the agent cannot rely on them.

| Source | What it provides |
|--------|-----------------|
| `<integration>/metadata.csv` | The full set of metrics the integration collects — tells the agent what data must exist to make metric values non-zero |
| `<integration>/manifest.json` | Integration display name, tags, categories — context for documentation searches |
| Vendor documentation (WebFetch/WebSearch) | Service topology requirements, configuration, resource minimums |
| Docker Hub (WebFetch) | Canonical image names, available tags, recommended versions |

### What the agent produces

The agent writes a complete `tests/lab/` subtree under the integration directory:

```
<integration>/
  lab.yaml                            ← machine-readable manifest (see Section 4)
  tests/
    lab/
      RESEARCH.md                     ← human-readable narrative (see below)
      compose/
        docker-compose.yml            ← service(s) + Datadog Agent as Docker services
      seed/
        01_<description>.sh           ← numbered, idempotent, ordered
        02_<description>.py
        ...
      load/
        locustfile.py                 ← or k6_script.js
      agent/
        conf.yaml                     ← Datadog Agent integration config (instances, logs)
      healthcheck/
        check_<service>.sh            ← custom healthcheck scripts (script type only)
      provision/                      ← bare-metal and cluster runtimes only
        install_<service>.yml         ← Ansible playbook
        teardown_<service>.yml
```

Additionally, the agent produces a **starter Pulumi program** (`infra/labs/<integration>/`) that a team member reviews and merges alongside the integrations-core artifacts (see Section 7).

### RESEARCH.md — human-readable narrative

`lab.yaml` is clean YAML with no inline comments. The agent's reasoning lives in `tests/lab/RESEARCH.md` instead. This file explains:

- What this technology is and how it is typically deployed in production
- Why specific choices were made — instance type, service topology, partition counts, network configuration
- Which metrics each seed script targets (referenced from `metadata.csv`)
- Operational gotchas identified in the vendor documentation
- Links to the specific documentation pages and Docker Hub tags consulted

The human reviewer reads `RESEARCH.md` to audit the agent's reasoning without needing to repeat the research. When the lab is updated for a new tech version, the agent rewrites the affected sections of `RESEARCH.md` alongside the affected artifacts.

### Re-generation

`ddev lab research --update kafka --version 3.8` diffs against the existing artifacts. The agent fetches the new version's changelog and release notes, identifies changed APIs or configuration keys, and updates the affected files. Unchanged files are left untouched.

---

## 4. The `lab.yaml` Schema

`lab.yaml` is the machine-readable manifest. It declares infrastructure, healthchecks, execution order, and Agent configuration. All narrative explaining the choices lives in `RESEARCH.md`.

```yaml
metadata:
  integration: kafka
  tech_version: "3.7"
  generated_at: "2026-05-05"

infrastructure:
  cloud: aws
  runtime:
    type: compose
    file: tests/lab/compose/docker-compose.yml

healthchecks:
  - name: kafka-broker
    type: tcp
    host: localhost
    port: 9092
    timeout: 120s
    interval: 5s
  - name: zookeeper
    type: tcp
    host: localhost
    port: 2181
    timeout: 60s
    interval: 5s

seed:
  - type: script
    path: tests/lab/seed/01_create_topics.sh
  - type: script
    path: tests/lab/seed/02_produce_sample_events.py

load:
  driver: locust
  script: tests/lab/load/locustfile.py
  target_rps: 20

agent:
  image: datadog/agent:latest
  config: tests/lab/agent/conf.yaml
  api_key_secret: agent-integrations-dev/datadog-api-key
```

### Bare-metal runtime example (Oracle)

```yaml
infrastructure:
  cloud: aws
  runtime:
    type: bare-metal
    provisioner: tests/lab/provision/install_oracle.yml
    teardown: tests/lab/provision/teardown_oracle.yml

agent:
  image: datadog/agent:latest
  config: tests/lab/agent/conf.yaml
  api_key_secret: agent-integrations-dev/datadog-api-key
```

### Cluster runtime example (Lustre)

```yaml
metadata:
  integration: lustre
  tech_version: "2.15"

infrastructure:
  cloud: aws
  runtime:
    type: cluster
    nodes:
      - role: mgs_mds
        count: 1
        instance_type: r6i.xlarge
      - role: oss
        count: 2
        instance_type: r6i.xlarge
      - role: client
        count: 1
        instance_type: t3.large
    network:
      lnet_port: 988
    provisioner: tests/lab/provision/install_lustre_cluster.yml
    teardown: tests/lab/provision/teardown_lustre_cluster.yml

healthchecks:
  - name: mgs
    type: script
    script: tests/lab/healthcheck/check_mgs.sh
    timeout: 180s
    interval: 10s
  - name: mds
    type: script
    script: tests/lab/healthcheck/check_mds.sh
    timeout: 180s
    interval: 10s
  - name: oss
    type: script
    script: tests/lab/healthcheck/check_oss.sh
    timeout: 180s
    interval: 10s
```

---

## 5. Healthcheck Mechanism

### Stage 1 — SSH readiness

Before any healthcheck from `lab.yaml` runs, the CLI polls for SSH availability on port 22 of each provisioned instance. This catches instance boot failures, user-data script crashes, and provisioning delays. Timeout is fixed at 5 minutes per instance; if SSH isn't available by then, `ddev lab create` aborts and prints the cloud console log for diagnosis.

### Stage 2 — Service readiness

Each entry in `healthchecks` is polled independently until it passes or times out. All entries must pass before seed scripts begin. For cluster runtimes, healthchecks run against their respective nodes using the IP map produced by Pulumi (see Section 7).

Supported healthcheck types:

| Type | Mechanism | When to use |
|------|-----------|-------------|
| `tcp` | TCP connection to `host:port` | Databases, message brokers, simple servers |
| `http` | HTTP GET, expect `200` (or configurable status) | REST APIs, management UIs |
| `script` | SSH + run script, expect exit code 0 | Complex readiness checks (cluster quorum, replication lag, Lustre mount state) |

Healthcheck scripts live in `tests/lab/healthcheck/` and are part of the research phase output.

### Failure behavior

If any healthcheck times out, `ddev lab create` prints which check failed, shows the last N lines of the relevant service log (via SSH), and exits non-zero. Instances are left running for manual inspection. `ddev lab destroy <integration>` still works to clean up.

---

## 6. The Datadog Agent in the Lab

Every lab provisions a Datadog Agent configured to run the integration check continuously. This is the primary artifact of the lab — the goal is to see real metrics flowing into Datadog from a live service.

### Compose runtime

The Agent runs as a service in `tests/lab/compose/docker-compose.yml`, generated by the research phase:

```yaml
services:
  kafka:
    image: confluentinc/cp-kafka:3.7.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181

  zookeeper:
    image: confluentinc/cp-zookeeper:3.7.0

  datadog-agent:
    image: ${DD_AGENT_IMAGE:-datadog/agent:latest}
    environment:
      DD_API_KEY: ${DD_API_KEY}
      DD_SITE: datadoghq.com
    volumes:
      - ./agent/conf.yaml:/etc/datadog-agent/conf.d/kafka.d/conf.yaml:ro
    depends_on:
      kafka:
        condition: service_healthy
```

The `DD_AGENT_IMAGE` environment variable defaults to `datadog/agent:latest`, allowing version overrides without editing the compose file.

### Bare-metal and cluster runtimes

The Agent runs as a Docker container on one of the EC2 instances (the client node for cluster runtimes). The Ansible provisioner installs Docker if not present, pulls the Agent image, and starts it with the same volume mount pattern.

### Updating the Agent

```bash
ddev lab upgrade <integration> --agent 7.57.0
# Pulls datadog/agent:7.57.0 on the instance, restarts the container, verifies the check runs.

ddev lab upgrade <integration> --integration 16.2.0
# Updates the integration package inside the Agent container to the specified version.
```

`ddev lab upgrade` does not reprovision instances or re-seed data. It only restarts the Agent container with the new image or package.

---

## 7. Infrastructure — Pulumi Automation API

### Why Pulumi

The infrastructure provisioning layer must be multi-cloud (AWS today, GCP in future sprints) and must execute on demand — not auto-applied on merge. The [Pulumi Automation API](https://www.pulumi.com/docs/using-pulumi/automation-api/) satisfies both:

- **Multi-cloud**: the same Python program targets AWS or GCP by selecting a provider; switching is a `cloud:` field in `lab.yaml`
- **On-demand**: `ddev lab create` calls `pulumi.up()` directly via the Python SDK — no external CI/CD trigger, no separate repo with auto-apply
- **In-repo**: Pulumi programs live in `ddev/src/ddev/cli/lab/infra/` (Python), eliminating the cloud-inventory dependency
- **State in object storage**: stack state stored in S3 (`aws`) or GCS (`gcp`) under `agent-integrations-dev-lab-state/pulumi/<integration>/`

### Pulumi program structure

```
ddev/src/ddev/cli/lab/
  infra/
    __init__.py
    base.py              ← abstract LabInfra class (provision, destroy, outputs)
    aws.py               ← AWS provider implementation
    gcp.py               ← GCP provider implementation (Phase 2+)
    cluster.py           ← multi-node cluster logic (node roles, security groups, IP map)
```

The research phase generates a starter Pulumi program and places it in `infra/labs/<integration>/` inside the same PR as the `tests/lab/` artifacts. A team member reviews it before merging — same review gate as any other generated artifact.

### What the Pulumi program provisions

**Single-instance (compose and bare-metal runtimes):**
- VM instance (EC2 or GCE) + security group (SSH + service ports, ingress from team VPN CIDR only)
- IAM instance profile / service account for Secrets Manager access
- Object storage bucket for seed artifacts and license files
- Cost-attribution tags: `team = agent-integrations`, `env = lab`

**Cluster runtime (Lustre, Kafka, Cassandra):**
- VPC + subnet shared by all nodes
- Security group with `lnet_port` (or equivalent) open between all instances in the group
- Instances launched per role (from `lab.yaml` nodes list)
- Outputs a `{role → [ip, ...]}` map used by subsequent steps

### Cluster provisioning flow (Lustre example)

Because LNET configuration requires each node to know the actual IP addresses of other nodes, provisioning follows a two-phase approach:

```
1. pulumi up  →  launch all nodes, emit {role → [ip, ...]} map
2. Render Ansible inventory + vars from IP map
3. ansible-playbook install_lustre_cluster.yml  (all nodes in parallel where possible)
     Stage A: install kernel modules + lnet tools on all nodes
     Stage B: configure lnet.conf with actual NIDs on all nodes
     Stage C: start MGS → start MDS → start OSS → mount client
4. Healthchecks run against per-role nodes
5. Seed scripts run on client node
6. Agent container starts on client node
```

The Ansible playbook receives the IP map via `--extra-vars`. Startup order (MGS before OSS before client mount) is encoded in the playbook's play sequence.

### Registry entry

```json
{
  "kafka": {
    "owner": "david.kirov@datadoghq.com",
    "cloud": "aws",
    "instance_ids": ["i-0abc123"],
    "instance_ips": {"primary": "10.0.1.42"},
    "pulumi_stack": "agent-integrations/kafka",
    "started_at": "2026-05-05T10:30:00Z",
    "last_active_at": "2026-05-07T09:15:00Z",
    "tech_version": "3.7",
    "agent_version": "7.56.2",
    "status": "running"
  }
}
```

---

## 8. CLI — `ddev lab`

### Full command surface

```bash
# Lab lifecycle
ddev lab create <integration>              # provision → healthcheck → seed → load → Agent
ddev lab stop <integration>                # stop load + services, leave instances running
ddev lab start <integration>              # restart services + load on a stopped lab
ddev lab destroy <integration>            # full teardown: services → pulumi destroy → deregister
ddev lab reload <integration>             # re-run seed scripts without reprovisioning

# Visibility
ddev lab list                              # all labs (all owners), with status
ddev lab status <integration>             # instance state, service health, Agent check status
ddev lab logs <integration> [service]     # tail logs from a service or the Agent
ddev lab ssh <integration>                # open SSH session

# Updates
ddev lab upgrade <integration> --agent <version>        # update Agent image
ddev lab upgrade <integration> --integration <version>  # update integration package

# Research phase
ddev lab research <integration>                          # generate all artifacts
ddev lab research --update <integration> --version <v>  # update for a new tech version
```

### `ddev lab create` flow

```
1.  Read <integration>/lab.yaml
2.  pulumi up  (Pulumi Automation API, state in S3/GCS)
3.  Poll port 22 on each instance until SSH is available (5 min max)
4.  For bare-metal / cluster runtime: ansible-playbook install_<service>.yml
    (cluster: with rendered IP map as extra-vars, plays run in role order)
5.  For each healthcheck in parallel: poll until pass or timeout
6.  For each seed script in order: ssh <ip> "bash -s" < tests/lab/seed/<script>
7.  Fetch DD_API_KEY from Secrets Manager
8.  For bare-metal / cluster: docker run -d datadog/agent on client node with conf volume
9.  For compose: DD_API_KEY=<key> docker compose up -d (Agent service included)
10. ssh <ip> "nohup <load driver> ..." to start background load
11. Write lab entry to shared registry (S3)
12. Print: instance IP(s), SSH command, Agent container name, Datadog dashboard URL
```

### `ddev lab destroy` flow

```
1.  ssh <ip>: pkill -f locust (or k6)
2.  For compose runtime: docker compose down --volumes
3.  For bare-metal / cluster: ansible-playbook teardown_<service>.yml
4.  pulumi destroy  (removes all cloud resources for the stack)
5.  Remove integration entry from S3 registry
```

### `ddev lab stop` / `ddev lab start`

`stop` halts services without destroying instances. Useful for saving costs overnight:

```
stop: ssh → stop load → docker compose stop (or systemd stop)
      → update registry status to "stopped"

start: ssh → docker compose start (or systemd start)
       → re-run all healthchecks → restart load generator
       → update registry status to "running"
```

### Shared lab registry

Lives in S3 (`s3://agent-integrations-dev-lab-state/registry.json`), visible to the whole team. `ddev lab list` renders it as a table with status indicators. Any team member can destroy a lab they don't own but is prompted to confirm.

---

## 9. Research Artifact Conventions

### Directory layout

```
<integration>/
  lab.yaml
  tests/
    lab/
      RESEARCH.md               ← human-readable: topology rationale, metric coverage,
                                   operational gotchas, documentation sources
      compose/
        docker-compose.yml      ← service topology + Agent service
      seed/
        01_<description>.sh     ← numbered, idempotent, ordered
        02_<description>.py
        ...
      load/
        locustfile.py           ← or k6_script.js
      agent/
        conf.yaml               ← Datadog Agent integration config
      healthcheck/
        check_<service>.sh      ← custom healthcheck scripts (script type only)
      provision/                ← bare-metal and cluster runtimes only
        install_<service>.yml
        teardown_<service>.yml
```

### Seed script conventions

- Numbered prefix controls execution order
- Must be idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE TOPIC IF NOT EXISTS`)
- `RESEARCH.md` documents which metrics from `metadata.csv` each script targets
- Secrets (passwords, license keys) come from environment variables injected via IAM instance profile / service account, never hardcoded

### Load generator conventions

- Locust is the default; k6 for protocols Locust doesn't support natively (e.g., raw Kafka protocol)
- `target_rps` from `lab.yaml` sets the load level
- Load daemon logs to `/var/log/ddev-lab-load.log` on the instance

### Agent config conventions

`tests/lab/agent/conf.yaml` follows standard Datadog integration config format, pre-filled with connection details matching the compose file or bare-metal installation (localhost, standard ports, credentials from environment variables).

---

## 10. Phased Rollout

| Phase | Scope | Success criteria |
|-------|-------|-----------------|
| 1 | CLI skeleton: `create`, `stop`, `destroy`, `list`, `status` + shared registry + Kafka as reference (research artifacts hand-written, Pulumi program hand-written) | Team member runs `ddev lab create kafka` and sees Agent metrics in Datadog |
| 2 | `ddev lab research` command + research agent | Agent produces complete `tests/lab/` + `RESEARCH.md` for Kafka from docs alone; diff against hand-written is minimal |
| 3 | Research + runtime for Oracle and IBM MQ (bare-metal, Ansible provisioner) | `ddev lab create oracle` works end-to-end including teardown |
| 4 | Lustre cluster support (cluster runtime, multi-node Pulumi + LNET Ansible provisioner) | `ddev lab create lustre` provisions 3+1 node cluster, Agent reports filesystem metrics |
| 5 | GCP provider + `ddev lab upgrade` + cost controls (auto-stop after 7 days of inactivity) | `cloud: gcp` in `lab.yaml` works; team can update Agent version without reprovisioning |

---

## 11. Open Questions

1. **Pulumi state backend** — S3 bucket `agent-integrations-dev-lab-state` needs to be created and access policy set. Who owns this in AWS? Confirm with cloud-infrastructure team before Phase 1.
2. **AMI / base image maintenance** — who owns Ubuntu 22.04 base image rotation for EC2 (and equivalent for GCP)? Platform team or agent-integrations?
3. **Datadog API key in the lab** — the Agent should emit to a dedicated org/environment (e.g., `agent-integrations-labs` in the sandbox org) to avoid polluting production metric streams. Confirm with Datadog-internal infra team.
4. **Lustre kernel modules** — the `install_lustre_cluster.yml` playbook needs to install `lustre-server` and `lustre-client` kernel modules. These may require a specific kernel version pinned in the AMI. Confirm requirements with whoever last set up a Lustre test environment (see internal Confluence page for prior art).
5. **Cost controls** — auto-stop after 7 days of inactivity via a scheduled Lambda or `ddev lab gc`? Where does the Lambda live if not in cloud-inventory?
6. **CI integration** — `ddev lab create` callable from CI for long-running E2E suites? If yes, registry needs a `ci_run_id` field and auto-destroy on pipeline completion.
