# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


class Limiter(object):
    def __init__(self, object_name, object_limit, warning_func=None):
        self.warning = warning_func
        self.name = object_name
        self.limit = object_limit

        self.reached_limit = False
        self.count = 0
        self.seen = set()

    def reset(self):
        self.reached_limit = False
        self.count = 0
        self.seen.clear()

    def is_reached(self, uid=None):
        if self.reached_limit:
            return True

        if uid:
            if uid in self.seen:
                return False
            self.count += 1
            self.seen.add(uid)
        else:
            self.count += 1

        if self.count > self.limit:
            if self.warning:
                self.warning("Exceeded limit of {} {}, ignoring next ones".format(self.limit, self.name))
            self.reached_limit = True
            return True
        return False

    def get_status(self):
        return (self.count, self.limit, self.reached_limit)
