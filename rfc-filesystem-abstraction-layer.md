# OS Abstraction Layer for Datadog Integrations

| Field | Value |
| --- | --- |
| Authors | Noueman Khalikine |
| Team | Agent Integrations |
| Date | 2026-08-04 |
| Shepherd | TBD |
| Reviewers | Agent Integrations |
| Status | Ready for review |

## Overview

Integrations accept inputs that are paths: a file to read, a `bin_dir`, a path to a binary the check
executes. Those inputs reach `open`, `os`, `shutil`, `glob`, and `subprocess` at scattered call sites with no
validation. This document proposes a single OS interface in `datadog_checks_base` through which those
operations run, so every input-derived path and executable is checked in one place before use.

The trusted-provider mechanism already decides *whether* a path input is acceptable, based on how much the
config provider is trusted. This proposal does not change that decision; it moves where the decision is
applied.

## Problem Description

An untrusted config provider that controls a path input can turn a check into an exploit in two ways.

The first is path traversal: a file-path input pointed outside its intended directory reads or writes
arbitrary files. The second, more serious, is remote code execution, where a binary-path input is pointed at
an attacker-chosen executable that the check then runs. This is not hypothetical. `slurm` executes binaries
resolved from a configurable `slurm_binaries_dir` and per-command `*_path` options; `ceph` runs a
configurable `ceph_cmd`; `glusterfs` runs a `gstatus_path`; `gunicorn` runs a configurable `gunicorn`
binary. Several of these wrap the configured binary in `sudo`, so the attacker-chosen program is not even the
first element of the command.

The trusted-provider mechanism applies its decision to config *fields*, at load time. That leaves two gaps.
It does not govern the file or exec operation performed later, and it cannot see paths derived at runtime
from something other than a single config field. Because the affected access is spread across roughly forty
check packages, there is no central place to apply the same decision at the moment the path is actually used.

Two expected claims do not hold. `<JAVA_BIN_PATH>` in JMX integrations is not an instance of this problem, as
no JMX integration executes it from Python; JMXFetch launches the JVM Agent-side, beyond any Python
interface's reach. And the exposure is not repository-wide: it sits in about forty of roughly 260 check
packages, which is what makes a phased migration tractable.

> [Open question: the motivation also rests on specific path-traversal and symlink findings in integrations
> that are not yet public. Reviewers with access should confirm those before this is approved, since the RCE
> examples above are the only part of the motivation evidenced by code in the repository.]

## Stakeholders

**Owner.** The Agent Integrations team owns both the interface and the threat model it implements, and is
responsible for the migration.

**Must approve.** The owners of the trusted-provider mechanism and `SecurityConfig`, since this reuses their
policy rather than defining its own and adds one Agent setting controlling when that policy applies at point
of use. Owners of the Agent's security posture have an interest too, as this changes when a check can fail.

**Must be informed.** Maintainers of the affected integrations, whose tests may need mock-target updates. And
operators already running config-field validation, who need to know that point-of-use enforcement is a
separate switch defaulting to off, so nothing changes for them until they opt in.

**Merely affected.** The remaining integrations, which do no direct I/O, and `ddev`, which gains one command.

## Requirements

Parity is the hard requirement. With validation disabled, the default, every operation must behave exactly as
the call it replaces: identical exception types and timing, permission bits, encodings, laziness, and return
values. Acceptance per integration is that existing test assertions pass unchanged in behavior, allowing only
mock-target updates where a test patched a module-level import the migration relocates. About a third of
migrated integrations need one, and a shared test fixture keeps those edits mechanical. Parity is all this
proves; enforcement needs its own tests, and has them where binaries come from config.

Enforcement must be independently controllable, through its own Agent setting with three modes: off, which
evaluates nothing; log, which evaluates the policy and reports what would be denied without blocking; and
enforce, which denies. Off is the default. This matters because reusing the existing field-validation flag
would mean any operator who has already enabled it begins enforcing at every migrated call site the moment
this ships, with no gradual path and no way to observe the impact first. An unrecognized mode must be treated
as off and reported, so a typo can neither enforce unexpectedly nor break a check.

The validator must invent no allowlist policy; it reuses `SecurityConfig` exactly as load-time validation
does. One behavior is necessarily new: a bare command name is not a path, so it is resolved through `PATH`
first, because that is the program the OS will run. Without this, every check invoking a bare name would break
the moment enforcement is enabled.

Coverage must be honest rather than assumed. Every operation consuming an input path or binary must be
expressible through the interface *and* reached through the binding that enforces, or else be counted as
unguarded. Unguarded sites are acceptable where the path cannot come from configuration, but must be
deliberate and recorded rather than accidental. This is checked mechanically, not by review.

Finally, the interface must coexist with what exists. It retains `get_subprocess_output` as its own operation
rather than folding it into a generic `run`, because that helper's output decoding, empty-output handling, and
logging are observable behavior. It must not disturb `tailfile`, `persistent_cache`, or `secrets`.

## Design Notes

Three decisions are worth recording, because each prevents a specific way this could look correct while
enforcing nothing.

**Two bindings, only one of which enforces.** The interface is reachable from a check, bound to that check's
security configuration, and as a module-level singleton bound to the no-op validator for code with no check
instance. Only the first enforces, so a mechanical rename is not sufficient: substituting the singleton at a
config-derived call site preserves parity and passes every test while enforcing nothing, which is worse than
an obvious bypass because it resembles coverage. Module-level helpers touching config-derived paths therefore
take the interface as a required parameter.

**Validate what actually launches, not the first argument.** Several checks wrap a config-derived binary in
`sudo`, putting the attacker-controlled program second, so validation covers every program the command will
launch. The same applies to `shell=True`, where the shell is what launches and so what is validated. Shell
strings are not parsed, so those sites count as unguarded rather than as coverage they lack.

**Library handoffs are validated at the handoff.** Where a library opens a path itself, the read cannot be
intercepted, so the path is validated at the last point the check controls and passed through unchanged.
Normalizing it there would rewrite a relative path to an absolute one and change what the library receives,
which parity forbids. Validating without mediating the read is weaker than mediation, which is why the
boundary below sits where it does.

## Out of Scope

This is a mediation layer for direct standard-library I/O. It is deliberately not a containment boundary, and
the difference is a permanent ceiling on its value rather than a gap to be closed later.

A Python-level wrapper cannot intercept a path opened inside a third-party library, anything a subprocess does
once launched, or what a shell string executes. Validating at the handoff narrows the first case without
closing it. Restricting an already-approved binary is the operating system's job, not this layer's.

Also out of scope: defining new security policy, since the trusted-provider model is reused as-is; adding size
limits the existing policy does not express; and migrating every affected integration at once. The direct-I/O
surface spans roughly forty check packages, about seventy-five counting library handoffs, phased across them.

## Open Questions

- Should any integration ever be permitted to use `shell=True` with a config-derived string? Under
  enforcement this requires allowlisting the shell, which grants everything the shell can reach. No
  integration does this today, and the alternative is to forbid it outright.
- What is the supported Python version floor?
- Should the log-only mode emit a metric or event, rather than only a log line, so a fleet's violations can
  be assessed centrally before enforcement is enabled?
