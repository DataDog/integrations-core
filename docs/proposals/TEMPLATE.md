# YOUR TITLE HERE

- Authors: your names here
- Date: 2000-01-01
- Status: draft|review|accepted|rejected
- [Discussion][1]

## Overview

*A paragraph concisely describing the problem you need to solve and and your
recommended solution. A tl/dr as the kids say. For example:*

The Agent should be able to run checks written in Python. This is a proposal to
embed CPython using `cgo`, so checks would run within the same process as the
Agent itself.

## Problem

*If necessary, add a more detailed sketch of the problem. Add any notes,
pictures, text, or details that illuminate why this is a problem that needs to be 
solved. Keep it as concise as possible.*

## Constraints

*If necessary, note any constraints or requirements that any solution must
fulfill. For example:*

    1. Target is Python 2.7.
    2. Memory footprint should not increase more than 10%.
    3. Every check in `integrations-core` and `integrations-extra` should be
       supported.

## Recommended Solution

*Describe your solution in the bare minimum detail to be understood. Explain
why it's better than the current implementation and better than other options. Address
any critical operational issues (failure modes, failover, redundancy, performance, cost).
For example:*

Embedding CPython is a well known, documented and supported practice which is quite
common for C applications. The same C api can be leveraged using cgo...

- Strengths
  - easily share memory between Go and Python
- Weaknesses
  - adapt Go's concurrency model to Python threading execution model might cause
    issues
  - cross compiling isn't available anymore
  - a Python crash would bring down the Agent
- Performance
  - ...
- Cost
  - 4Mb of memory footprint are added
    - ...

## Other Solutions

*Describe a few other options to solve problem.*

- Spawn a Python process for each check and use gRPC to communicate.
  - At each collection cycle the Agent would fork a Python process running a check...

## Open Questions

*Note any big questions that don’t yet have an answer that might be relevant.*

## Appendix

*Link any relevant stats, code, images, whatever that work for you.*
[1]: https://github.com/DataDog/datadog-agent/pull/0
