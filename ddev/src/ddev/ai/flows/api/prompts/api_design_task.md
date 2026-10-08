---
type: prompt
name: api_design_task
---
Research and design the API integration for **${integration}**.

## PRD

${prd}

Apply your standing API-integration design contract to these inputs. Read applicable repository
guidance, relevant reference integrations, and official vendor sources. Before declaring
the design ready, check the derived integration identity for validity and collision, and check
every required PRD item against the evidence gathered: operations, fields, metric sources,
logs/events mechanisms, pagination, Agent behavior, and the test environment.

Complete all verification during this task, while tools are available. Resolve required evidence
gaps, or call `stop_flow` as your design contract describes.

If every required behavior has a well-supported, implementable contract, the entire final response
must be exactly:

Design status: READY

Do not append a design report, tables, implementation plan, or handoff to this response; the
memory step writes the handoff once from this conversation. Do not create or edit integration
files during design.
