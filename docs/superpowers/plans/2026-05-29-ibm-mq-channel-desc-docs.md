# IBM MQ channel_desc Partial Coverage Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a troubleshooting entry and config option clarification documenting that `channel_desc` only appears on channel definition metrics (not status metrics) when `add_description_tags: true` is enabled.

**Architecture:** Three files change in `integrations-core/ibm_mq/`: README.md gets a new troubleshooting section; `assets/configuration/spec.yaml` gets an expanded `add_description_tags` description; `datadog_checks/ibm_mq/data/conf.yaml.example` gets the same expansion in comment form. A changelog fragment is created. No code changes.

**Tech Stack:** Markdown, YAML, `ddev` CLI (validation)

---

## Background

When `add_description_tags: true` is enabled, IBM MQ's PCF protocol only returns the channel description field (`MQCACH_DESC`) in `MQCMD_INQUIRE_CHANNEL` (definition) responses — not in `MQCMD_INQUIRE_CHANNEL_STATUS` (status) responses. The integration's guard at `channel_metric_collector.py:73` and `:169` silently skips the tag when the field is absent. Result: definition metrics get `channel_desc`, status metrics don't. This is correct behavior but was never documented.

**Metrics that get `channel_desc`** (from `MQCMD_INQUIRE_CHANNEL`): `ibm_mq.channel.batch_size`, `ibm_mq.channel.batch_interval`, `ibm_mq.channel.sharing_conversations`, `ibm_mq.channel.long_retry`, `ibm_mq.channel.short_retry`, `ibm_mq.channel.long_timer`, `ibm_mq.channel.short_timer`, `ibm_mq.channel.keep_alive_interval`, `ibm_mq.channel.hb_interval`, `ibm_mq.channel.max_msg_length`.

**Metrics that do NOT get `channel_desc`** (from `MQCMD_INQUIRE_CHANNEL_STATUS`): `ibm_mq.channel.channel_status`, `ibm_mq.channel.msgs`, `ibm_mq.channel.bytes_sent`, `ibm_mq.channel.bytes_rcvd`, `ibm_mq.channel.buffers_rcvd`, `ibm_mq.channel.buffers_sent`, `ibm_mq.channel.batches`, `ibm_mq.channel.current_msgs`, `ibm_mq.channel.mca_status`, `ibm_mq.channel.indoubt_status`, `ibm_mq.channel.conn_status`, `ibm_mq.channel.ssl_key_resets`, `ibm_mq.channel.count`, `ibm_mq.channel.connections_active`, the channel service check.

`queue_desc` is NOT affected — the queue collector already cross-injects the description tag from the definition call into the status and reset calls.

---

## File Map

| File | Change |
|------|--------|
| `ibm_mq/README.md` | Add new `### channel_desc tag not appearing on all channel metrics` entry in the Troubleshooting section, before `### Other` |
| `ibm_mq/assets/configuration/spec.yaml` | Expand `add_description_tags` description to note the PCF split and which metrics are affected |
| `ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example` | Same expansion as spec.yaml, in YAML comment form |
| `ibm_mq/changelog.d/<PR_NUMBER>.doc` | Create after PR is opened; content: one-sentence summary |

---

## Task 1: Add troubleshooting entry to README.md

**Files:**
- Modify: `ibm_mq/README.md` lines 311-312 (the `### Other` heading)

- [ ] **Step 1: Open README.md and find the insertion point**

The new entry goes between the `### Warnings in the logs` section and `### Other`. In the current file, `### Other` is at line 311. Insert the new section immediately before it.

- [ ] **Step 2: Add the new troubleshooting entry**

Insert the following block immediately before the `### Other` heading (line 311 of the current file):

```markdown
### `channel_desc` tag not appearing on all channel metrics

When `add_description_tags: true` is enabled, the `channel_desc` tag only appears on some `ibm_mq.channel.*` metrics. This is expected behavior caused by how IBM MQ's PCF protocol works.

The integration uses two separate PCF commands to collect channel data:

- **`MQCMD_INQUIRE_CHANNEL`** (channel definition inquiry): IBM MQ includes the description field (`MQCACH_DESC`) in these responses. Metrics from this command receive `channel_desc`.
- **`MQCMD_INQUIRE_CHANNEL_STATUS`** (runtime status inquiry): IBM MQ does **not** include the description field in these responses. Metrics from this command do not receive `channel_desc`.

Metrics that **receive** `channel_desc`: `ibm_mq.channel.batch_size`, `ibm_mq.channel.batch_interval`, `ibm_mq.channel.sharing_conversations`, `ibm_mq.channel.long_retry`, and other channel definition metrics.

Metrics that **do not receive** `channel_desc`: `ibm_mq.channel.channel_status`, `ibm_mq.channel.msgs`, `ibm_mq.channel.bytes_sent`, `ibm_mq.channel.bytes_rcvd`, `ibm_mq.channel.buffers_rcvd`, `ibm_mq.channel.buffers_sent`, `ibm_mq.channel.batches`, `ibm_mq.channel.current_msgs`, `ibm_mq.channel.count`, `ibm_mq.channel.connections_active`, and other runtime status metrics.

No configuration change can add `channel_desc` to status metrics — this is a constraint of IBM MQ's PCF protocol, not of the Datadog Agent configuration.

**Note**: `queue_desc` does not have this limitation. All `ibm_mq.queue.*` metrics consistently receive `queue_desc` when `add_description_tags: true`.

```

(Leave a blank line after the block, then `### Other` follows.)

- [ ] **Step 3: Validate the README**

```bash
cd ~/dd/integrations-core
ddev validate readmes ibm_mq
```

Expected output:
```
All 1 READMEs are valid!
```

If it fails, fix any Markdown formatting issues reported and re-run until it passes.

- [ ] **Step 4: Commit**

```bash
cd ~/dd/integrations-core
git add ibm_mq/README.md
git commit -m "ibm_mq: document channel_desc PCF split in troubleshooting"
```

---

## Task 2: Update spec.yaml add_description_tags description

**Files:**
- Modify: `ibm_mq/assets/configuration/spec.yaml` lines 232–243 (the `add_description_tags` parameter block)

- [ ] **Step 1: Open spec.yaml and find the add_description_tags block**

The current block (lines 232–243) reads:

```yaml
- name: add_description_tags
  description: |
    Add description tags to channel and queue metrics. When enabled, the following tags will be added:
      - channel_desc:<description> for channel metrics
      - queue_desc:<description> for queue metrics

    Note: Enabling this option may increase tag cardinality depending on how many unique
    descriptions you have configured for your channels and queues.
  value:
    example: false
    type: boolean
```

- [ ] **Step 2: Replace the `description:` block (lines 233–239) with the expanded version**

Use the Edit tool. The `old_string` to match is the entire current `description: |` block:

```yaml
        description: |
          Add description tags to channel and queue metrics. When enabled, the following tags will be added:
            - channel_desc:<description> for channel metrics
            - queue_desc:<description> for queue metrics

          Note: Enabling this option may increase tag cardinality depending on how many unique
          descriptions you have configured for your channels and queues.
```

Replace with:

```yaml
        description: |
          Add description tags to channel and queue metrics. When enabled, the following tags will be added:
            - channel_desc:<description> for channel metrics
            - queue_desc:<description> for queue metrics

          For channel metrics, `channel_desc` is only added to channel definition metrics (such as
          `ibm_mq.channel.batch_size`). It is not added to channel status metrics (such as
          `ibm_mq.channel.channel_status` or `ibm_mq.channel.msgs`), because IBM MQ's
          `MQCMD_INQUIRE_CHANNEL_STATUS` PCF response does not return the channel description field.
          No configuration change can work around this — it is a constraint of IBM MQ's PCF protocol.
          See the integration troubleshooting documentation for details.

          `queue_desc` is applied consistently to all `ibm_mq.queue.*` metrics and is not affected by
          this limitation.

          Note: Enabling this option may increase tag cardinality depending on how many unique
          descriptions you have configured for your channels and queues.
```

The full updated block should look like (preserving the 6-space list-item indent from the surrounding file):

```yaml
      - name: add_description_tags
        description: |
          Add description tags to channel and queue metrics. When enabled, the following tags will be added:
            - channel_desc:<description> for channel metrics
            - queue_desc:<description> for queue metrics

          For channel metrics, `channel_desc` is only added to channel definition metrics (such as
          `ibm_mq.channel.batch_size`). It is not added to channel status metrics (such as
          `ibm_mq.channel.channel_status` or `ibm_mq.channel.msgs`), because IBM MQ's
          `MQCMD_INQUIRE_CHANNEL_STATUS` PCF response does not return the channel description field.
          No configuration change can work around this — it is a constraint of IBM MQ's PCF protocol.
          See the integration troubleshooting documentation for details.

          `queue_desc` is applied consistently to all `ibm_mq.queue.*` metrics and is not affected by
          this limitation.

          Note: Enabling this option may increase tag cardinality depending on how many unique
          descriptions you have configured for your channels and queues.
        value:
          example: false
          type: boolean
```

- [ ] **Step 3: Validate the config**

```bash
cd ~/dd/integrations-core
ddev validate config ibm_mq
```

Expected output:
```
Validating default configuration files for 1 checks...
All 2 configuration files are valid!
```

If it fails, the spec.yaml syntax is wrong — check YAML indentation (spec.yaml uses 2-space indent, `description: |` is a literal block scalar).

- [ ] **Step 4: Commit**

```bash
cd ~/dd/integrations-core
git add ibm_mq/assets/configuration/spec.yaml
git commit -m "ibm_mq: clarify channel_desc PCF split in add_description_tags spec"
```

---

## Task 3: Update conf.yaml.example add_description_tags comment

**Files:**
- Modify: `ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example` lines 188–196

- [ ] **Step 1: Open conf.yaml.example and find the add_description_tags block**

The current block (lines 188–196) reads:

```yaml
## @param add_description_tags - boolean - optional - default: false
## Add description tags to channel and queue metrics. When enabled, the following tags will be added:
##   - channel_desc:<description> for channel metrics
##   - queue_desc:<description> for queue metrics
##
## Note: Enabling this option may increase tag cardinality depending on how many unique
## descriptions you have configured for your channels and queues.
#
# add_description_tags: false
```

- [ ] **Step 2: Replace the comment block with the expanded version**

```yaml
## @param add_description_tags - boolean - optional - default: false
## Add description tags to channel and queue metrics. When enabled, the following tags will be added:
##   - channel_desc:<description> for channel metrics
##   - queue_desc:<description> for queue metrics
##
## For channel metrics, `channel_desc` is only added to channel definition metrics (such as
## `ibm_mq.channel.batch_size`). It is not added to channel status metrics (such as
## `ibm_mq.channel.channel_status` or `ibm_mq.channel.msgs`), because IBM MQ's
## `MQCMD_INQUIRE_CHANNEL_STATUS` PCF response does not return the channel description field.
## No configuration change can work around this — it is a constraint of IBM MQ's PCF protocol.
## See the integration troubleshooting documentation for details.
##
## `queue_desc` is applied consistently to all `ibm_mq.queue.*` metrics and is not affected by
## this limitation.
##
## Note: Enabling this option may increase tag cardinality depending on how many unique
## descriptions you have configured for your channels and queues.
#
# add_description_tags: false
```

- [ ] **Step 3: Validate the config**

```bash
cd ~/dd/integrations-core
ddev validate config ibm_mq
```

Expected output:
```
Validating default configuration files for 1 checks...
All 2 configuration files are valid!
```

- [ ] **Step 4: Commit**

```bash
cd ~/dd/integrations-core
git add ibm_mq/datadog_checks/ibm_mq/data/conf.yaml.example
git commit -m "ibm_mq: clarify channel_desc PCF split in conf.yaml.example"
```

---

## Task 4: Create changelog fragment and open PR

**Files:**
- Create: `ibm_mq/changelog.d/<PR_NUMBER>.doc`

- [ ] **Step 1: Open the PR first to get a PR number**

Use the `commit-commands:commit-push-pr` skill or the `integrations-core-pr-workflow` skill to push the branch and open the PR. The PR title should be:

```
[ibm_mq] Document channel_desc partial coverage for add_description_tags
```

PR description should reference AGENT-16288 internally and explain that `channel_desc` is intentionally absent from channel status metrics due to the IBM MQ PCF protocol.

- [ ] **Step 2: Create the changelog fragment**

Once you have the PR number (e.g., `23800`), create the file:

```bash
# Replace 23800 with the actual PR number
cat > ~/dd/integrations-core/ibm_mq/changelog.d/23800.doc <<'EOF'
Document that `channel_desc` is only applied to channel definition metrics when `add_description_tags` is enabled, due to IBM MQ's PCF protocol not returning the description field in `MQCMD_INQUIRE_CHANNEL_STATUS` responses.
EOF
```

- [ ] **Step 3: Commit and push the changelog fragment**

```bash
cd ~/dd/integrations-core
git add ibm_mq/changelog.d/
git commit -m "ibm_mq: add changelog fragment for channel_desc doc update"
git push
```

- [ ] **Step 4: Verify CI passes**

Check GitHub Actions on the PR. The relevant jobs are:
- `validate-config` — verifies conf.yaml.example
- `validate-readmes` — verifies README.md

If CI fails, read the job logs and fix reported issues.
