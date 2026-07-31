# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Override the generated discovery candidates() for this integration.
#
# Define a candidates(service, default) function to wrap or replace the generated
# candidate generation. `default` is the generated generator; call it to reuse
# the spec-driven candidates, or ignore it to replace them entirely.
#
# def candidates(service, default):
#     yield from default(service)
