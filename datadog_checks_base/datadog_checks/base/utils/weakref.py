import weakref
from collections import deque


class WeakDeque(deque):
    def __init__(self, iterable):
        super(WeakDeque, self).__init__(weakref.ref(i) for i in iterable)

    def append(self, x):
        super(WeakDeque, self).append(weakref.ref(x))

    def appendleft(self, x):
        super(WeakDeque, self).appendleft(weakref.ref(x))

    def extend(self, iterable):
        super(WeakDeque, self).extend(weakref.ref(i) for i in iterable)

    def extendleft(self, iterable):
        super(WeakDeque, self).extendleft(weakref.ref(i) for i in iterable)

    def pop(self, *args):
        return super(WeakDeque, self).pop(*args)()

    def popleft(self):
        return super(WeakDeque, self).popleft()()

    def remove(self, *args):
        raise NotImplemented('Method not implemented')

