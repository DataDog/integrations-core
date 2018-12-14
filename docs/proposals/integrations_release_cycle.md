# Integrations release cycle

- Authors: Massimiliano Pippi
- Date: 2018-12-12
- Status: draft
- [Discussion](https://github.com/DataDog/integrations-core/pull/2741)

## Overview

Each agent based integration has its own version number and can be released as
a Python package at any given time. This document outlines what the release
cycle will be for each integration.

## Problem

At this moment the release cycle for most of the integration is not formalized
and there's no process in place to keep it consistent and reliable. Once a feature
or a bugfix is merged on `master`, different things may happen:

- A release is immediately triggered.
- A release is triggered after merging other, maybe unrelated changes for the same integration.
- A release is triggered at a later time without any specific deadline.

This causes a number of issues for all actors involved:

- Engineers have to improvise on a case by case basis.
- Contributors have no idea if changes within a PR will be released and when.
- Users don't know when a feature or a bugfix will be actually available.

## Constraints

1. Each integration must keep its own release cycle.
2. The solutions must work for integrations from `integrations-extra` as well.

## Recommended Solution

A release must be immediately triggered after merging a PR into the `master` branch.
To ensure quality of the software shipped, **changes on the branch should be tested before merging**.
A pre-release testing checklist is out of the scope of this RFC but in general
an engineer must consider that changes in a PR could be used right after the
release by any users on any supported Agent version and platform.

- **Strengths**:
  - Well defined release process, predictable and reliable.
  - Process can be heavily automated in the future.
  - Pre-release testing is distributed during the release cycle instead of piled during Agent release week.
  - Agent release is easier to manage from the integrations standpoint.
  - Ownership of a release would be clear: the same person would review, test, merge and release.
  
- **Weaknesses**:
  - A fair amount of work might be needed to properly test releases since we might have many.
  - For each release of an integration, the `CHANGELOG.md` would most likely list only one item.

## Other Solutions

- **Wait some time before releasing something that was merged on `master`**
  - How much time?
  - Not sure who will be the release owner: the person who merged the first PR? The person who merged the last?
  - We should probably still do pre-release testing before merging, so review time would be the same as the proposed solution.
  - During the Agent release week, we might have few integrations in an unreleased state, a code freeze would likely be required.
  
- **Release with a fixed schedule**
  - Very hard if not impossible to implement since `integrations-core` already hosts more than 100 different packages.
