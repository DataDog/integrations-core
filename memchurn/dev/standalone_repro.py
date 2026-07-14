#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Standalone driver for the memchurn allocation engine.

Runs the same malloc/free churn as the ``memchurn`` Agent check, but with no
dependency on ``datadog_checks`` so it can be run on any Linux box to sanity-check
the engine and to A/B allocators::

    python standalone_repro.py --workers 48 --runs 20
    LD_PRELOAD=/path/to/libjemalloc.so.2 python standalone_repro.py --workers 48 --runs 20

Under glibc, RSS climbs and plateaus well above the retained bytes (fragmentation).
Under jemalloc, RSS tracks much closer to the retained bytes.

This mirrors ``datadog_checks/memchurn/check.py``; the check keeps its engine
self-contained on purpose, so the two intentionally duplicate a little logic.
"""
from __future__ import annotations

import argparse
import ctypes
import math
import os
import random
import threading
import time
from collections import deque

MIB = 1024 * 1024


class Libc:
    def __init__(self) -> None:
        libc = ctypes.CDLL(None, use_errno=False)
        malloc = libc.malloc
        malloc.restype = ctypes.c_void_p
        malloc.argtypes = [ctypes.c_size_t]
        free = libc.free
        free.restype = None
        free.argtypes = [ctypes.c_void_p]
        self._malloc = malloc
        self._free = free
        self._libc = libc

    def allocate(self, size: int) -> int | None:
        ptr = self._malloc(size)
        if not ptr:
            return None
        ctypes.memset(ptr, 1, size)
        return int(ptr)

    def release(self, ptr: int) -> None:
        self._free(ptr)

    def arena_count(self) -> int | None:
        try:
            malloc_info = self._libc.malloc_info
        except AttributeError:
            return None
        try:
            import tempfile

            malloc_info.argtypes = [ctypes.c_int, ctypes.c_void_p]
            self._libc.fopen.restype = ctypes.c_void_p
            self._libc.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self._libc.fclose.argtypes = [ctypes.c_void_p]
            fd, path = tempfile.mkstemp(suffix='.xml')
            os.close(fd)
            try:
                fp = self._libc.fopen(path.encode(), b'w')
                if not fp:
                    return None
                malloc_info(0, fp)
                self._libc.fclose(fp)
                with open(path, 'rb') as handle:
                    return handle.read().count(b'<heap ')
            finally:
                os.unlink(path)
        except Exception:
            return None


class Engine:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.libc = Libc()
        self._lock = threading.Lock()
        self._shutdown = threading.Event()
        self.live_bytes = 0
        self.retained_bytes = 0
        self._log_lo = math.log(args.min_bytes)
        self._log_hi = math.log(args.max_bytes)
        self.workers = [Worker(i, self) for i in range(args.workers)]
        for worker in self.workers:
            worker.thread.start()

    def draw_size(self) -> int:
        if random.random() < 0.85:
            frac = random.random() * 0.6
        else:
            frac = 0.6 + random.random() * 0.4
        size = int(math.exp(self._log_lo + frac * (self._log_hi - self._log_lo)))
        return min(self.args.max_bytes, max(self.args.min_bytes, size))

    def reserve(self, size: int) -> bool:
        with self._lock:
            if self.live_bytes + size > self.args.max_total_bytes:
                return False
            self.live_bytes += size
            return True

    def unreserve(self, size: int) -> None:
        with self._lock:
            self.live_bytes -= size

    def note_retained(self, size: int) -> None:
        with self._lock:
            self.retained_bytes += size

    def run_once(self) -> None:
        deadline = time.monotonic() + self.args.run_budget
        for worker in self.workers:
            worker.trigger(deadline)
        for worker in self.workers:
            worker.done.wait(timeout=max(0.0, deadline + 1.0 - time.monotonic()))
        self._enforce_retained_cap()
        self._thread_churn()

    def _enforce_retained_cap(self) -> None:
        with self._lock:
            over = self.retained_bytes - self.args.max_retained_bytes
        if over <= 0:
            return
        freed = 0
        while freed < over:
            progressed = False
            for worker in self.workers:
                size = worker.drop_oldest_retained()
                if size is None:
                    continue
                with self._lock:
                    self.retained_bytes -= size
                freed += size
                progressed = True
                if freed >= over:
                    break
            if not progressed:
                break

    def _thread_churn(self) -> None:
        threads = [
            threading.Thread(target=self._churn_once, daemon=True) for _ in range(self.args.thread_churn)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=self.args.run_budget)

    def _churn_once(self) -> None:
        size = self.draw_size()
        if not self.reserve(size):
            return
        ptr = self.libc.allocate(size)
        if ptr is None:
            self.unreserve(size)
            return
        if self.args.hold_ms:
            time.sleep(self.args.hold_ms / 1000.0)
        self.libc.release(ptr)
        self.unreserve(size)

    def shutdown(self) -> None:
        self._shutdown.set()
        for worker in self.workers:
            worker.go.set()
        for worker in self.workers:
            worker.thread.join(timeout=1.0)


class Worker:
    def __init__(self, index: int, engine: Engine) -> None:
        self.engine = engine
        self.retained: deque[tuple[int, int]] = deque()
        self.go = threading.Event()
        self.done = threading.Event()
        self.deadline = 0.0
        self.thread = threading.Thread(target=self._loop, name=f'memchurn-worker-{index}', daemon=True)

    def trigger(self, deadline: float) -> None:
        self.deadline = deadline
        self.done.clear()
        self.go.set()

    def _loop(self) -> None:
        while not self.engine._shutdown.is_set():
            self.go.wait()
            self.go.clear()
            if self.engine._shutdown.is_set():
                break
            try:
                self._run_burst()
            finally:
                self.done.set()

    def _run_burst(self) -> None:
        engine = self.engine
        transient: list[tuple[int, int]] = []
        for _ in range(engine.args.allocations_per_worker):
            if time.monotonic() >= self.deadline:
                break
            size = engine.draw_size()
            if not engine.reserve(size):
                if transient:
                    self._free_random(transient)
                    continue
                break
            ptr = engine.libc.allocate(size)
            if ptr is None:
                engine.unreserve(size)
                continue
            if engine.args.hold_ms:
                time.sleep(engine.args.hold_ms / 1000.0)
            if random.random() < engine.args.retained_fraction:
                self.retained.append((ptr, size))
                engine.note_retained(size)
            else:
                transient.append((ptr, size))
            if transient and random.random() < 0.5:
                self._free_random(transient)
        random.shuffle(transient)
        for ptr, size in transient:
            engine.libc.release(ptr)
            engine.unreserve(size)

    def _free_random(self, transient: list[tuple[int, int]]) -> None:
        ptr, size = transient.pop(random.randrange(len(transient)))
        self.engine.libc.release(ptr)
        self.engine.unreserve(size)

    def drop_oldest_retained(self) -> int | None:
        if not self.retained:
            return None
        ptr, size = self.retained.popleft()
        self.engine.libc.release(ptr)
        self.engine.unreserve(size)
        return size


def rss_bytes() -> int | None:
    try:
        with open('/proc/self/statm') as handle:
            return int(handle.read().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    except (OSError, IndexError, ValueError):
        pass
    try:
        import resource

        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        is_macos = hasattr(os, 'uname') and os.uname().sysname == 'Darwin'
        return max_rss if is_macos else max_rss * 1024
    except Exception:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workers', type=int, default=48)
    parser.add_argument('--runs', type=int, default=20)
    parser.add_argument('--allocations-per-worker', type=int, default=256)
    parser.add_argument('--min-bytes', type=int, default=512)
    parser.add_argument('--max-bytes', type=int, default=4 * MIB)
    parser.add_argument('--retained-fraction', type=float, default=0.1)
    parser.add_argument('--max-retained-bytes', type=int, default=256 * MIB)
    parser.add_argument('--max-total-bytes', type=int, default=1024 * MIB)
    parser.add_argument('--hold-ms', type=float, default=0.0)
    parser.add_argument('--thread-churn', type=int, default=8)
    parser.add_argument('--run-budget', type=float, default=5.0)
    parser.add_argument('--interval', type=float, default=0.0, help='seconds to sleep between runs')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    baseline = rss_bytes()
    print(f"platform baseline RSS: {_mb(baseline)} MiB, threads: {threading.active_count()}")
    engine = Engine(args)
    print(f"started {args.workers} worker threads; total threads: {threading.active_count()}\n")

    header = f"{'run':>4} {'threads':>8} {'rss_MiB':>10} {'retained_MiB':>13} {'live_MiB':>10} {'arenas':>7}"
    print(header)
    print('-' * len(header))
    try:
        for run in range(1, args.runs + 1):
            engine.run_once()
            arenas = engine.libc.arena_count()
            print(
                f"{run:>4} {threading.active_count():>8} {_mb(rss_bytes()):>10} "
                f"{engine.retained_bytes / MIB:>13.1f} {engine.live_bytes / MIB:>10.1f} "
                f"{('n/a' if arenas is None else arenas):>7}"
            )
            if args.interval:
                time.sleep(args.interval)
    finally:
        engine.shutdown()

    final_rss = rss_bytes()
    print()
    print(f"final RSS: {_mb(final_rss)} MiB, retained: {engine.retained_bytes / MIB:.1f} MiB")
    if final_rss is not None and engine.retained_bytes:
        print(f"RSS / retained ratio: {final_rss / max(1, engine.retained_bytes):.2f}x (higher => more fragmentation)")


def _mb(value: int | None) -> str:
    return 'n/a' if value is None else f"{value / MIB:.1f}"


if __name__ == '__main__':
    main()
