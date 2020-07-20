import weakref
from collections import deque


class WeakDeque(object):
    """
    Weakref implementation of Deque

    Caveat:
        - Some deque methods are not implemented.
    """
    def __init__(self, iterable):
        self.deq = deque(weakref.ref(i) for i in iterable)

    def append(self, x):
        self.deq.append(weakref.ref(x))

    def appendleft(self, x):
        self.deq.appendleft(weakref.ref(x))

    def extend(self, iterable):
        self.deq.extend(weakref.ref(i) for i in iterable)

    def extendleft(self, iterable):
        self.deq.extendleft(weakref.ref(i) for i in iterable)

    def pop(self, *args):
        while True:
            val = self.deq.pop(*args)()
            if val is not None:
                return val

    def popleft(self):
        while True:
            val = self.deq.popleft()()
            if val is not None:
                return val

    def __len__(self):
        return len(self.deq)
