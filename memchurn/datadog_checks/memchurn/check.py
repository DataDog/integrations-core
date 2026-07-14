# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Synthetic memory-churn check that reproduces glibc arena fragmentation.

The check drives real C ``malloc``/``free`` traffic from many long-lived worker
threads with the GIL released, mirroring the allocation behavior of natively
backed checks (``postgres``/psycopg2, ``kafka_consumer``/librdkafka). The metrics
it emits are incidental; only its allocation behavior matters.

This module is intentionally self-contained: it imports only the Python standard
library, ``ctypes``, and ``datadog_checks.base`` so it can be dropped in as a
single-file ``checks.d/memchurn.py`` as well as installed as a package.
"""
from __future__ import annotations

import ctypes
import math
import os
import random
import threading
import time
from collections import deque

from datadog_checks.base import AgentCheck, is_affirmative

# Buffers at or above glibc's default mmap threshold are serviced by mmap rather
# than the arena heap; drawing sizes across this boundary exercises both paths.
GLIBC_MMAP_THRESHOLD_BYTES = 128 * 1024

DEFAULTS = {
    'num_workers': 48,
    'allocations_per_worker': 256,
    'min_alloc_bytes': 512,
    'max_alloc_bytes': 4 * 1024 * 1024,
    'retained_fraction': 0.1,
    'max_retained_bytes': 256 * 1024 * 1024,
    'max_total_bytes': 1024 * 1024 * 1024,
    'hold_ms': 0.0,
    'thread_churn_per_run': 8,
    'run_budget_seconds': 5.0,
}


class Libc:
    """Thin wrapper over libc ``malloc``/``free``/``memset`` via ctypes.

    Each foreign call releases the GIL, so allocations issued from multiple
    worker threads genuinely run in parallel at the C level.
    """

    def __init__(self) -> None:
        libc = ctypes.CDLL(None, use_errno=False)

        # Setting restype is mandatory: without it ctypes assumes c_int and the
        # 64-bit pointer returned by malloc is truncated, which crashes on free.
        malloc = libc.malloc
        malloc.restype = ctypes.c_void_p
        malloc.argtypes = [ctypes.c_size_t]

        free = libc.free
        free.restype = None
        free.argtypes = [ctypes.c_void_p]

        self._malloc = malloc
        self._free = free
        self._libc = libc

    def allocate(self, size: int, touch: bool) -> int | None:
        """Allocate ``size`` bytes; optionally touch every page so it is resident."""
        ptr = self._malloc(size)
        if not ptr:
            return None
        if touch:
            ctypes.memset(ptr, 1, size)
        return int(ptr)

    def release(self, ptr: int) -> None:
        self._free(ptr)

    def arena_count(self) -> int | None:
        """Best-effort glibc arena count via ``malloc_info`` (None off glibc)."""
        return _glibc_arena_count(self._libc)


class Worker:
    """A long-lived allocator thread that owns its own set of live buffers.

    Owning buffers per-thread is what makes glibc hand each worker its own
    malloc arena, exactly as broker/connection threads do in native checks.
    """

    def __init__(self, index: int, check: MemChurnCheck) -> None:
        self.index = index
        self._check = check
        self.retained: deque[tuple[int, int]] = deque()
        self.go = threading.Event()
        self.done = threading.Event()
        self.deadline = 0.0
        self.alloc_calls = 0
        self.free_calls = 0
        self.thread = threading.Thread(
            target=self._loop, name=f'memchurn-worker-{index}', daemon=True
        )

    def start(self) -> None:
        self.thread.start()

    def trigger(self, deadline: float) -> None:
        self.deadline = deadline
        self.alloc_calls = 0
        self.free_calls = 0
        self.done.clear()
        self.go.set()

    def _loop(self) -> None:
        while not self._check.shutdown.is_set():
            self.go.wait()
            self.go.clear()
            if self._check.shutdown.is_set():
                break
            try:
                self._run_burst()
            finally:
                self.done.set()

    def _run_burst(self) -> None:
        check = self._check
        transient: list[tuple[int, int]] = []
        for _ in range(check.allocations_per_worker):
            if time.monotonic() >= self.deadline:
                break

            size = check.draw_size()
            if not check.reserve(size):
                # Over the global ceiling: make room by freeing a live transient
                # buffer (non-LIFO) rather than growing the heap further.
                if transient:
                    self._free_random(transient)
                    continue
                break

            ptr = check.libc.allocate(size, check.touch_pages)
            if ptr is None:
                check.unreserve(size)
                continue
            self.alloc_calls += 1

            if check.hold_ms:
                time.sleep(check.hold_ms / 1000.0)

            if random.random() < check.retained_fraction:
                self.retained.append((ptr, size))
                check.note_retained(size)
            else:
                transient.append((ptr, size))

            # Interleave frees so the heap is pockmarked with holes while the
            # burst is still running, rather than freed cleanly at the end.
            if transient and random.random() < 0.5:
                self._free_random(transient)

        # Free whatever transient buffers remain, in shuffled (non-LIFO) order so
        # glibc cannot simply coalesce them back off the top of the heap.
        random.shuffle(transient)
        for ptr, size in transient:
            check.libc.release(ptr)
            check.unreserve(size)
            self.free_calls += 1

    def _free_random(self, transient: list[tuple[int, int]]) -> None:
        ptr, size = transient.pop(random.randrange(len(transient)))
        self._check.libc.release(ptr)
        self._check.unreserve(size)
        self.free_calls += 1

    def drop_oldest_retained(self) -> int | None:
        """Free the oldest retained buffer; return its size, or None if empty."""
        if not self.retained:
            return None
        ptr, size = self.retained.popleft()
        self._check.libc.release(ptr)
        self._check.unreserve(size)
        self.free_calls += 1
        return size

    def free_all(self) -> None:
        while self.retained:
            ptr, _ = self.retained.popleft()
            self._check.libc.release(ptr)


class MemChurnCheck(AgentCheck):
    __NAMESPACE__ = 'memchurn'

    def __init__(self, name: str, init_config: dict, instances: list[dict]) -> None:
        super().__init__(name, init_config, instances)

        inst = self.instance or {}
        self.num_workers = max(1, int(inst.get('num_workers', DEFAULTS['num_workers'])))
        self.allocations_per_worker = max(
            1, int(inst.get('allocations_per_worker', DEFAULTS['allocations_per_worker']))
        )
        self.min_alloc_bytes = max(1, int(inst.get('min_alloc_bytes', DEFAULTS['min_alloc_bytes'])))
        self.max_alloc_bytes = max(
            self.min_alloc_bytes, int(inst.get('max_alloc_bytes', DEFAULTS['max_alloc_bytes']))
        )
        self.retained_fraction = min(
            1.0, max(0.0, float(inst.get('retained_fraction', DEFAULTS['retained_fraction'])))
        )
        self.max_retained_bytes = max(
            0, int(inst.get('max_retained_bytes', DEFAULTS['max_retained_bytes']))
        )
        self.max_total_bytes = max(
            self.max_alloc_bytes, int(inst.get('max_total_bytes', DEFAULTS['max_total_bytes']))
        )
        self.hold_ms = max(0.0, float(inst.get('hold_ms', DEFAULTS['hold_ms'])))
        self.thread_churn_per_run = max(
            0, int(inst.get('thread_churn_per_run', DEFAULTS['thread_churn_per_run']))
        )
        self.run_budget_seconds = max(
            0.1, float(inst.get('run_budget_seconds', DEFAULTS['run_budget_seconds']))
        )
        self.touch_pages = is_affirmative(inst.get('touch_pages', True))
        self._tags = list(inst.get('tags') or [])

        self._log_lo = math.log(self.min_alloc_bytes)
        self._log_hi = math.log(self.max_alloc_bytes)

        self.shutdown = threading.Event()
        self._accounting_lock = threading.Lock()
        self._live_bytes = 0
        self._retained_bytes = 0
        self._workers: list[Worker] = []

        self.libc: Libc | None = None
        try:
            self.libc = Libc()
        except (OSError, AttributeError, ValueError) as e:
            self.log.warning(
                "memchurn could not bind libc malloc/free (%s); the check will no-op on this "
                "platform. It targets Linux/glibc.",
                e,
            )

    def draw_size(self) -> int:
        """Draw a byte size biased toward small/medium with a heavy large tail."""
        # 85% of draws land in the lower ~60% of log-space (small/medium); the
        # remaining 15% form a long tail that crosses the mmap threshold.
        if random.random() < 0.85:
            frac = random.random() * 0.6
        else:
            frac = 0.6 + random.random() * 0.4
        size = int(math.exp(self._log_lo + frac * (self._log_hi - self._log_lo)))
        return min(self.max_alloc_bytes, max(self.min_alloc_bytes, size))

    def reserve(self, size: int) -> bool:
        """Reserve headroom against the global ceiling; False if it would breach."""
        with self._accounting_lock:
            if self._live_bytes + size > self.max_total_bytes:
                return False
            self._live_bytes += size
            return True

    def unreserve(self, size: int) -> None:
        with self._accounting_lock:
            self._live_bytes -= size

    def note_retained(self, size: int) -> None:
        with self._accounting_lock:
            self._retained_bytes += size

    def _build_pool(self) -> None:
        self._workers = [Worker(i, self) for i in range(self.num_workers)]
        for worker in self._workers:
            worker.start()
        self.log.info("memchurn started %d persistent allocator threads", self.num_workers)

    def _run_bursts(self) -> None:
        deadline = time.monotonic() + self.run_budget_seconds
        for worker in self._workers:
            worker.trigger(deadline)
        # Give workers the full budget plus a small grace period to wind down.
        wait_deadline = deadline + 1.0
        for worker in self._workers:
            worker.done.wait(timeout=max(0.0, wait_deadline - time.monotonic()))

    def _enforce_retained_cap(self) -> None:
        with self._accounting_lock:
            over = self._retained_bytes - self.max_retained_bytes
        if over <= 0:
            return
        freed = 0
        while freed < over:
            progressed = False
            for worker in self._workers:
                size = worker.drop_oldest_retained()
                if size is None:
                    continue
                with self._accounting_lock:
                    self._retained_bytes -= size
                freed += size
                progressed = True
                if freed >= over:
                    break
            if not progressed:
                break

    def _run_thread_churn(self) -> None:
        threads = [
            threading.Thread(target=self._churn_once, name=f'memchurn-churn-{i}', daemon=True)
            for i in range(self.thread_churn_per_run)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=self.run_budget_seconds)

    def _churn_once(self) -> None:
        """Short-lived thread that allocates once, touches it, then exits.

        A fresh thread that allocates forces glibc to cycle an arena for it,
        mimicking per-connection churn.
        """
        size = self.draw_size()
        if not self.reserve(size):
            return
        ptr = self.libc.allocate(size, self.touch_pages)
        if ptr is None:
            self.unreserve(size)
            return
        if self.hold_ms:
            time.sleep(self.hold_ms / 1000.0)
        self.libc.release(ptr)
        self.unreserve(size)

    def check(self, _: dict) -> None:
        if self.libc is None:
            self.gauge('workers', 0, tags=self._tags)
            return

        if not self._workers:
            self._build_pool()

        self._run_bursts()
        self._enforce_retained_cap()
        if self.thread_churn_per_run:
            self._run_thread_churn()

        alloc_calls = sum(w.alloc_calls for w in self._workers)
        free_calls = sum(w.free_calls for w in self._workers)
        with self._accounting_lock:
            live_bytes = self._live_bytes
            retained_bytes = self._retained_bytes

        self.gauge('workers', len(self._workers), tags=self._tags)
        self.gauge('retained_bytes', retained_bytes, tags=self._tags)
        self.gauge('live_bytes', live_bytes, tags=self._tags)
        self.gauge('alloc_calls_last_run', alloc_calls, tags=self._tags)
        self.gauge('free_calls_last_run', free_calls, tags=self._tags)

        rss = _process_rss_bytes()
        if rss is not None:
            self.gauge('rss_bytes', rss, tags=self._tags)

        arenas = self.libc.arena_count()
        if arenas is not None:
            self.gauge('arenas', arenas, tags=self._tags)

    def cancel(self) -> None:
        """Tear down worker threads and free retained buffers on shutdown."""
        self.shutdown.set()
        for worker in self._workers:
            worker.go.set()
        for worker in self._workers:
            worker.thread.join(timeout=1.0)
        if self.libc is not None:
            for worker in self._workers:
                worker.free_all()


def _glibc_arena_count(libc: ctypes.CDLL) -> int | None:
    """Count glibc arenas by parsing ``malloc_info`` XML; None if unavailable."""
    try:
        malloc_info = libc.malloc_info
    except AttributeError:
        return None
    try:
        import tempfile

        malloc_info.argtypes = [ctypes.c_int, ctypes.c_void_p]
        malloc_info.restype = ctypes.c_int
        libc.fopen.restype = ctypes.c_void_p
        libc.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        libc.fclose.argtypes = [ctypes.c_void_p]

        fd, path = tempfile.mkstemp(suffix='.xml', prefix='memchurn-mallocinfo-')
        os.close(fd)
        try:
            fp = libc.fopen(path.encode(), b'w')
            if not fp:
                return None
            malloc_info(0, fp)
            libc.fclose(fp)
            with open(path, 'rb') as handle:
                data = handle.read()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        return data.count(b'<heap ')
    except Exception:
        return None


def _process_rss_bytes() -> int | None:
    """Return the process RSS in bytes on Linux/macOS, or None if unknown."""
    try:
        with open('/proc/self/statm') as handle:
            resident_pages = int(handle.read().split()[1])
        return resident_pages * os.sysconf('SC_PAGE_SIZE')
    except (OSError, IndexError, ValueError):
        pass
    try:
        import resource

        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # ru_maxrss is bytes on macOS, kilobytes on Linux.
        return max_rss if _is_macos() else max_rss * 1024
    except Exception:
        return None


def _is_macos() -> bool:
    return os.uname().sysname == 'Darwin' if hasattr(os, 'uname') else False
