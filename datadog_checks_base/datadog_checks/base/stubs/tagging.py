# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

class TaggerStub(object):
    LOW, ORCHESTRATOR, HIGH = range(3)

    def __init__(self):
        self.reset()

    def reset(self):
        self._store = {}
        self._calls = []
        self._default_tags = []

    def set_default_tags(self, default):
        self._default_tags = default

    def set_tags(self, tags):
        self._store = tags

    def assert_called(self, entity, cardinality):
        assert (entity, cardinality) in self._calls

    def tag(self, entity, cardinality):
        self._calls.append((entity, cardinality))
        # Match agent 6.5 behaviour of not accepting None
        if entity is None:
            raise ValueError("None is not a valid entity id")
        return self._store.get(entity, self._default_tags)[:]

    def get_tags(self, entity, high_card):
        if high_card:
            return self.tag(entity, self.HIGH)
        else:
            return self.tag(entity, self.LOW)

tagger = TaggerStub()
