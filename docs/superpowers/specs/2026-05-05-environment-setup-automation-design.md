# Environment Setup Automation Design

**Date:** 2026-05-05  
**Last revised:** 2026-05-07  
**Status:** Draft  
**Scope:** `ddev lab` — agentic framework for provisioning, seeding, and load-testing Datadog integration environments on remote EC2 infrastructure

---

## 1. Problem and Goals

Setting up environments for Datadog integrations is one of the highest-friction steps in integration development. The pain concentrates in three areas:

1. **Infrastructure complexity** — Some integrations (Oracle DB, IBM MQ, Kafka + ZooKeeper, Lustre clusters) require real VMs, licenses, or multi-node topologies that cannot run locally and require significant manual effort.
2. **Data quality** — Test datasets are minimal or absent; developers run checks against empty systems that don't reflect production behavior, masking metric collection gaps.
3. **Portability** — Environment setup knowledge is tribal. When a developer leaves or switches integrations, the environment has to be reconstructed from scratch.

### Goals

| Priority | Goal |
|----------|------|
| Primary | Provision a fully running integration environment on EC2 with a single command |
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
│    lab.yaml                  ← manifest + narrative              │
│    tests/lab/compose/        ← service topology (Docker)         │
│    tests/lab/seed/           ← numbered, idempotent scripts      │
│    tests/lab/load/           ← Locust or k6 script               │
│    tests/lab/agent/          ← Datadog Agent integration config  │
│    tests/lab/provision/      ← Ansible playbook (bare-metal only)│
│    [starter main.tf]         ← handed to cloud-inventory repo    │
└────────────────────────┬─────────────────────────────────────────┘
                         │  artifacts reviewed + committed
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  Deterministic Execution Layer  (ddev lab CLI)                   │
│                                                                  │
│  create:   terraform apply → wait SSH → healthchecks →           │
│            seed → load → start Agent → register                  │
│                                                                  │
│  stop:     stop load → docker compose down → update registry     │
│                                                                  │
│  destroy:  stop load → stop services → terraform destroy →       │
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
  lab.yaml                            ← manifest (see Section 4)
  tests/
    lab/
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
      provision/                      ← bare-metal runtimes only
        install_<service>.yml         ← Ansible playbook
```

Additionally, the agent produces a **starter `main.tf`** for the cloud-inventory repo (printed to stdout or saved to a staging path) that a cloud-infrastructure team member reviews and commits to `cloud-inventory/aws/agent-integrations-dev/labs/<integration>/`.

### YAML comments as narrative

Every non-obvious decision in `lab.yaml` and the generated scripts carries a YAML or shell comment explaining what the agent found in the documentation and why it made each choice (e.g., why a specific instance type, why a particular partition count, what metrics a given seed script targets). The human reviewer reads the comments to audit the agent's reasoning without needing to repeat the research.

### Re-generation

`ddev lab research --update kafka --version 3.8` diffs against the existing artifacts. The agent fetches the new version's changelog and release notes, identifies changed APIs or configuration keys, and updates the affected files. Unchanged files are left untouched.

---

## 4. The `lab.yaml` Schema

`lab.yaml` is the manifest. It declares infrastructure, healthchecks, execution order, and Agent configuration. The generated scripts it references are the actual implementation.

```yaml
# lab.yaml — generated by `ddev lab research`, reviewed by a human before merging.
# Comments in this file and in tests/lab/ explain every non-obvious decision.

metadata:
  integration: kafka
  tech_version: "3.7"
  generated_at: "2026-05-05"

infrastructure:
  # All labs run on EC2 — keeps environments shareable and off developer machines.
  # Terraform source lives in cloud-inventory; see Section 5.
  terraform:
    source: cloud-inventory/aws/agent-integrations-dev/labs/kafka
    region: us-east-1
    # t3.large: Kafka broker + ZooKeeper combined require ~4 GB RAM under load.
    # Upgrade to r5.xlarge if broker heap exceeds 2 GB.
    instance_type: t3.large

  runtime:
    # Docker Compose runs inside the EC2 instance.
    # For licensed software that can't be containerized, use type: bare-metal.
    type: compose
    file: tests/lab/compose/docker-compose.yml

# Each service in the topology gets its own healthcheck entry.
# Healthchecks run FROM the EC2 instance (via SSH), so "localhost" is the instance.
# Seeds and load only start after all healthchecks pass.
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
  # Seed scripts run in numbered order over SSH after all healthchecks pass.
  # Scripts must be idempotent — re-running ddev lab create must not fail.
  - type: script
    path: tests/lab/seed/01_create_topics.sh
    # Creates 10 topics with 3 partitions each to exercise kafka.partition.* metrics.
  - type: script
    path: tests/lab/seed/02_produce_sample_events.py
    # Produces 50k events across all topics to populate consumer group lag metrics.

load:
  # Continuous background load keeps metric values non-zero during Agent check runs.
  driver: locust                           # locust | k6
  script: tests/lab/load/locustfile.py
  # 20 RPS generates stable consumer lag without saturating a t3.large broker.
  target_rps: 20

agent:
  # Datadog Agent runs as a service in docker-compose.yml (compose runtime) or as
  # a standalone Docker container on the EC2 instance (bare-metal runtime).
  # The image tag is intentionally mutable — use `ddev lab upgrade` to update.
  image: datadog/agent:latest
  config: tests/lab/agent/conf.yaml
  # API key fetched from Secrets Manager at runtime; never stored in this file.
  api_key_secret: agent-integrations-dev/datadog-api-key
```

### Bare-metal runtime example (Oracle)

```yaml
infrastructure:
  terraform:
    source: cloud-inventory/aws/agent-integrations-dev/labs/oracle
    region: us-east-1
    instance_type: r5.xlarge             # Oracle minimum: 16 GB RAM
  runtime:
    type: bare-metal
    # Ansible installs Oracle from the license-gated S3 bucket.
    provisioner: tests/lab/provision/install_oracle.yml
    # Teardown runs the teardown playbook to deregister Oracle before terraform destroy.
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
  terraform:
    source: cloud-inventory/aws/agent-integrations-dev/labs/lustre
    region: us-east-1
    # Lustre requires a minimum 3-node cluster: MGS, MDS, and OSS.
    # Instance sizing from Lustre hardware guide: r6i.xlarge for MDS/OSS under test load.
    instance_type: r6i.xlarge

  runtime:
    type: bare-metal
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

### Stage 1 — EC2 SSH readiness

Before any healthcheck from `lab.yaml` runs, the CLI polls for SSH availability on port 22. This catches instance boot failures, user-data script crashes, and AMI provisioning delays. Timeout is fixed at 5 minutes; if SSH isn't available by then, `ddev lab create` aborts and prints the EC2 console log for diagnosis.

### Stage 2 — Service readiness

Each entry in `healthchecks` is polled independently until it passes or times out. All entries must pass before seed scripts begin.

Supported healthcheck types:

| Type | Mechanism | When to use |
|------|-----------|-------------|
| `tcp` | TCP connection to `host:port` | Databases, message brokers, simple servers |
| `http` | HTTP GET, expect `200` (or configurable status) | REST APIs, management UIs |
| `script` | SSH + run script, expect exit code 0 | Complex readiness checks (cluster quorum, replication lag, Lustre mount state) |

Healthcheck scripts live in `tests/lab/healthcheck/` and are part of the research phase output.

### Failure behavior

If any healthcheck times out, `ddev lab create` prints which check failed, shows the last N lines of the relevant service log (via SSH), and exits non-zero. The EC2 instance is left running for manual inspection. Running `ddev lab destroy <integration>` still works to clean up.

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
    # ... generated from vendor docs

  zookeeper:
    image: confluentinc/cp-zookeeper:3.7.0
    # ...

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

### Bare-metal runtime

The Agent runs as a Docker container on the EC2 instance alongside the bare-metal service. The Ansible provisioner installs Docker (if not present), pulls the Agent image, and starts it with the same volume mount pattern.

### Updating the Agent

```bash
ddev lab upgrade <integration> --agent 7.57.0
# Pulls datadog/agent:7.57.0 on the EC2 instance, restarts the container, verifies the check runs.

ddev lab upgrade <integration> --integration 16.2.0
# Updates the integration package inside the Agent container to the specified version.
```

`ddev lab upgrade` does not reprovision the EC2 instance or re-seed data. It only restarts the Agent container with the new image or package.

---

## 7. Infrastructure — Terraform in cloud-inventory

### Prerequisites

The CLI requires both repos to be configured in ddev:

```bash
ddev config set repos.core /path/to/integrations-core
ddev config set repos.cloud-inventory /path/to/cloud-inventory
```

`ddev lab` resolves Terraform source paths from `lab.yaml` relative to the `cloud-inventory` repo root.

### Directory layout

```
cloud-inventory/
  terraform-modules/
    integration-lab-ec2/           # recipe: single-instance lab
      main.tf
      variables.tf
      outputs.tf
    integration-lab-ec2-cluster/   # recipe: multi-node lab (Kafka, Lustre, Cassandra)
      main.tf
      variables.tf
      outputs.tf
  aws/
    agent-integrations-dev/
      labs/
        kafka/
          main.tf                  # calls integration-lab-ec2-cluster
          terraform.tfvars
        oracle/
          main.tf
          terraform.tfvars
        lustre/
          main.tf
          terraform.tfvars
```

### What the recipe modules handle

- EC2 instance(s) + security group (SSH + service ports, ingress from team VPN CIDR only)
- IAM instance profile for SSM access (fallback if SSH key is lost)
- S3 bucket for seed artifacts, load scripts, and license files
- CloudWatch log group for EC2 system logs
- `team = agent-integrations` and `env = lab` tags for cost attribution

### Integration-specific configs

Each `labs/<integration>/main.tf` calls the appropriate recipe module and sets:

- Instance type and count from `lab.yaml`
- AMI ID (Ubuntu 22.04 base, maintained by the platform team)
- Service-specific ports for the security group
- License file S3 paths (bare-metal runtimes only)

The research phase generates a starter `main.tf`. A cloud-infrastructure team member reviews and merges it into cloud-inventory separately from the integrations-core artifacts.

---

## 8. CLI — `ddev lab`

### Full command surface

```bash
# Lab lifecycle
ddev lab create <integration>              # provision → healthcheck → seed → load → Agent
ddev lab stop <integration>                # stop load + services, leave EC2 running
ddev lab start <integration>              # restart services + load on a stopped lab
ddev lab destroy <integration>            # full teardown: services → terraform destroy → deregister
ddev lab reload <integration>             # re-run seed scripts without reprovisioning

# Visibility
ddev lab list                              # all labs (all owners), with status
ddev lab status <integration>             # EC2 state, service health, Agent check status
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
2.  terraform apply in cloud-inventory/aws/agent-integrations-dev/labs/<integration>/
3.  Poll port 22 until SSH is available (5 min max)
4.  For bare-metal runtime: ansible-playbook tests/lab/provision/install_<service>.yml
5.  For each healthcheck in parallel: poll until pass or timeout
6.  For each seed script in order: ssh <ec2_ip> "bash -s" < tests/lab/seed/<script>
7.  Fetch DD_API_KEY from Secrets Manager
8.  For bare-metal: docker run -d datadog/agent on EC2 with conf volume
9.  For compose: DD_API_KEY=<key> docker compose up -d (Agent service included)
10. ssh <ec2_ip> "nohup <load driver> ..." to start background load
11. Write lab entry to shared registry (S3)
12. Print: EC2 IP, SSH command, Agent container name, Datadog integration dashboard URL
```

### `ddev lab destroy` flow

```
1.  ssh <ec2_ip>: pkill -f locust (or k6)              ← stop load generator
2.  For compose runtime: docker compose down --volumes  ← stop services + remove data
3.  For bare-metal: ansible-playbook teardown_<service>.yml  ← deregister + clean up
4.  terraform destroy in cloud-inventory/aws/.../labs/<integration>/
5.  Remove integration entry from S3 registry
```

### `ddev lab stop` / `ddev lab start`

`stop` halts services without destroying EC2. Useful for saving costs overnight:

```
stop: ssh → stop load → docker compose stop (or systemd stop)
      → update registry status to "stopped"

start: ssh → docker compose start (or systemd start)
       → re-run all healthchecks → restart load generator
       → update registry status to "running"
```

### Shared lab registry

Lives in S3 (`s3://agent-integrations-dev-lab-state/registry.json`), visible to the whole team:

```json
{
  "kafka": {
    "owner": "david.kirov@datadoghq.com",
    "ec2_instance_id": "i-0abc123",
    "ec2_ip": "10.0.1.42",
    "terraform_workspace": "kafka",
    "started_at": "2026-05-05T10:30:00Z",
    "last_active_at": "2026-05-07T09:15:00Z",
    "tech_version": "3.7",
    "agent_version": "7.56.2",
    "status": "running"
  }
}
```

Any team member can destroy a lab they don't own but is prompted to confirm. `ddev lab list` renders this as a table with status indicators.

---

## 9. Research Artifact Conventions

### Directory layout

```
<integration>/
  lab.yaml
  tests/
    lab/
      compose/
        docker-compose.yml        # service topology + Agent service
      seed/
        01_<description>.sh       # numbered, idempotent, ordered
        02_<description>.py
        ...
      load/
        locustfile.py             # or k6_script.js
      agent/
        conf.yaml                 # Datadog Agent integration config
      healthcheck/
        check_<service>.sh        # custom healthcheck scripts (script type only)
      provision/                  # bare-metal runtimes only
        install_<service>.yml
        teardown_<service>.yml
```

### Seed script conventions

- Numbered prefix controls execution order
- Must be idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE TOPIC IF NOT EXISTS`)
- Target specific metrics from `metadata.csv` — comments name which metrics each script enables
- Secrets (passwords, license keys) come from environment variables injected by the Terraform IAM instance profile, never hardcoded

### Load generator conventions

- Locust is the default; k6 for protocols Locust doesn't support natively (e.g., raw Kafka protocol)
- `target_rps` from `lab.yaml` sets the load level
- Load daemon logs to `/var/log/ddev-lab-load.log` on the EC2 instance

### Agent config conventions

`tests/lab/agent/conf.yaml` follows standard Datadog integration config format, pre-filled with connection details that match the compose file or bare-metal installation (localhost, standard ports, credentials from environment variables).

---

## 10. Phased Rollout

| Phase | Scope | Success criteria |
|-------|-------|-----------------|
| 1 | CLI skeleton: `create`, `stop`, `destroy`, `list`, `status` + shared registry + Kafka as reference (research artifacts hand-written) | Team member runs `ddev lab create kafka` and sees Agent metrics in Datadog |
| 2 | `ddev lab research` command + research agent | Agent produces complete `tests/lab/` for Kafka from docs alone; diff against hand-written is minimal |
| 3 | Research + runtime for Oracle and IBM MQ (bare-metal, Ansible provisioner) | `ddev lab create oracle` works end-to-end including teardown |
| 4 | Lustre cluster support (multi-instance Terraform + cluster healthchecks) | `ddev lab create lustre` provisions 3-node cluster, Agent reports filesystem metrics |
| 5 | `ddev lab upgrade`, cost controls (auto-stop after 7 days of inactivity) | Team can update Agent version without reprovisioning |

---

## 11. Open Questions

1. **Terraform state backend** — cloud-inventory uses its own remote state. Lab workspaces should use the same backend. Confirm with cloud-infrastructure team before Phase 1.
2. **AMI maintenance** — who owns Ubuntu 22.04 base AMI rotation? Platform team or agent-integrations?
3. **Datadog API key in the lab** — the API key for the Agent should emit to a dedicated org/environment (e.g., `agent-integrations-labs` in the sandbox org) to avoid polluting production metric streams. Confirm with the Datadog-internal infra team.
4. **Lustre licensing** — Lustre is open source but the cluster topology for production-like testing requires specific kernel modules on the AMI. Confirm AMI requirements with whoever last set up a Lustre test environment.
5. **Cost controls** — auto-stop after 7 days of inactivity via a Lambda in cloud-inventory or `ddev lab gc`?
6. **CI integration** — `ddev lab create` callable from CI for long-running E2E suites? If yes, registry needs a `ci_run_id` field and auto-destroy on pipeline completion.
