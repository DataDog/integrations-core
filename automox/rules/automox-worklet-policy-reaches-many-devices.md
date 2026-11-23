## Goal
Detect a worklet (script-running) policy created, updated or activated with a reach of many devices.

## Strategy
This rule fires when a `custom` or `required_software` policy is created, updated or activated with a device reach of 25 or more, read from `@ocsf.web_resources.data.server_count` on `Policy Created`, `Policy Configuration Updated` and `Policy Activated` (`@ocsf.class_uid:6001`). A worklet runs an arbitrary script as root or SYSTEM on every device it reaches, so a worklet with wide reach is a deployment channel for code execution across the fleet. Tune 25 to the environment. The signal is grouped by the policy (`@ocsf.web_resources.uid`).

## Triage and response
- Identify the policy and whether it runs a worklet script rather than applying vendor patches.
- Review the script's author and whether the change was an approved deployment.
- Determine how many devices the policy now targets.
- Check for an on-demand run of the policy shortly afterwards.
- If unexplained, deactivate the policy and review what it ran on the devices it reached.
