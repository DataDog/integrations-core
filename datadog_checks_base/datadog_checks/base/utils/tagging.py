# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

try:
    import tagger
except ImportError:
    from ..stubs import tagger

try:
    # Try to access the 6.11+ API
    tagger.tag("", tagger.ORCHESTRATOR)
except AttributeError:
    # 6.10 or lower, add a translation layer
    tagger.LOW, tagger.ORCHESTRATOR = False, False
    tagger.HIGH = True

    def tag(entity, card):
        return tagger.get_tags(entity, card)
    tagger.tag = tag
