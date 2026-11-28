## Goal
Detect a worklet (script-running) policy associated to a device group large enough to reach many devices.

## Strategy
This rule fires when a `custom` or `required_software` policy is associated to a group with a device reach of 25 or more, read from `@ocsf.entity.data.server_count` on `Policies Associated to Group` (`@ocsf.class_uid:3004`). A worklet runs an arbitrary script as root or SYSTEM on every device it reaches, so associating one with a large group turns it into a deployment channel for code execution across the fleet. Tune 25 to the environment. The signal is grouped by the policy (`@ocsf.entity.uid`).

## Triage and response
- Identify the policy and whether it runs a worklet script rather than applying vendor patches.
- Review the script's author and whether the association was an approved change.
- Determine which device group the policy now targets and how many devices that is.
- Check for an on-demand run of the policy shortly afterwards.
- If unexplained, remove the association and review what the policy ran on the devices it reached.
