# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Steady DNS workload for the coredns-full fixture (stdlib only).

Sends UDP DNS queries at fixed per-second rates, without waiting for answers,
so a slow or dead upstream never changes the send rate. Mid-run it changes
state once per state-like metric (see ../README.md, workload plan), and logs
the epoch time of each change so it can be matched against a scrape window.
"""

import os
import random
import select
import socket
import struct
import sys
import time

HOSTS = os.environ.get("DNS_HOSTS", "coredns").split()
PORT = int(os.environ.get("DNS_PORT", "53"))
CONF = os.environ.get("COREDNS_CONF_DIR", "/etc/coredns")
SEED = os.environ.get("COREDNS_SEED_DIR", "/seed")
T_HOT = int(os.environ.get("T_HOT_GROW", "450"))
T_BROKEN = int(os.environ.get("T_RELOAD_BROKEN", "500"))
T_RELOAD = int(os.environ.get("T_RELOAD_OK", "530"))
T_HOSTS = int(os.environ.get("T_HOSTS_GROW", "600"))

# Queries per second, per stream. Distinct rates: hot (cache hits) 5/s,
# miss names 2/s, slow names 2/s, dead-upstream names 0.5/s, hosts names 1/s.
HOT_RATE, FWD_RATE, HOSTS_RATE = 5, 2, 1
# slow.test queries per second: forward's max_concurrent 2 against a 4s upstream
# accepts ~0.5/s and rejects the rest (~1.5/s).
SLOW_RATE = 2
DEAD_EVERY = 2  # seconds
# Names answered with a 1s TTL (the cache keeps them 5s, its minimum), each
# re-queried every 15s: always a miss, and the cache holds a fixed number of
# entries instead of growing with every new name.
MISS_SET = 30


def log(msg):
    print(f"workload: {msg}", flush=True)


def log_change(t, message):
    """Logs a state change with its epoch time, to match it against a scrape window."""
    log(f"t={t:.0f}s epoch={time.time():.0f} {message}")


def query(name, qtype=1):
    qid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.strip(".").split(".")) + b"\0"
    return header + qname + struct.pack(">HH", qtype, 1)


def read(name):
    with open(os.path.join(SEED, name)) as f:
        return f.read()


def write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def write_corefile(fragment):
    """Writes the seed Corefile with `fragment` appended, so every variant shares one base."""
    write(os.path.join(CONF, "Corefile"), read("Corefile") + "\n" + read(fragment))


def resolve():
    """Returns the first name in HOSTS that resolves, with its address."""
    while True:
        for host in HOSTS:
            try:
                return host, (socket.gethostbyname(host), PORT)
            except OSError:
                pass
        time.sleep(1)


def main():
    if os.environ.get("ACTIVITY_GEN", "1") == "0":
        log("disabled via ACTIVITY_GEN=0; idling")
        while True:
            time.sleep(3600)

    host, addr = resolve()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    log(f"querying {host} at {addr}")
    start = time.monotonic()
    hot = 10
    done = set()
    i = 0
    while True:
        tick = time.monotonic()
        t = tick - start

        if t >= T_HOT and "hot" not in done:
            hot = 40
            done.add("hot")
            log_change(t, "hot set 10 -> 40 names")
        if t >= T_BROKEN and "broken" not in done:
            write_corefile("Corefile.broken")
            done.add("broken")
            log_change(t, "wrote an invalid Corefile (reload fails once)")
        if t >= T_RELOAD and "reload" not in done:
            write_corefile("Corefile.extra")
            done.add("reload")
            log_change(t, "wrote a valid Corefile with one more server block (reload succeeds)")
        if t >= T_HOSTS and "hosts" not in done:
            write(os.path.join(CONF, "hosts"), read("hosts.grown"))
            done.add("hosts")
            log_change(t, "hosts file 3 -> 6 entries")

        msgs = []
        msgs += [query(f"h{(i * HOT_RATE + k) % hot}.hot.example.test") for k in range(HOT_RATE)]
        msgs += [query(f"m{(i * FWD_RATE + k) % MISS_SET}.miss.example.test") for k in range(FWD_RATE)]
        msgs += [query(f"{'abcdef'[(i + k) % 6]}.hosts.test") for k in range(HOSTS_RATE)]
        msgs += [query(f"s{(i * SLOW_RATE + k) % MISS_SET}.slow.test") for k in range(SLOW_RATE)]
        if i % DEAD_EVERY == 0:
            msgs.append(query(f"d{(i // DEAD_EVERY) % MISS_SET}.dead.test"))

        failed, last_error = 0, None
        for m in msgs:
            try:
                sock.sendto(m, addr)
            except OSError as e:
                failed, last_error = failed + 1, e
        if failed:
            # One line per iteration, so a CoreDNS outage can't flood the log.
            log(f"t={t:.0f}s {failed}/{len(msgs)} sends failed: {last_error}")

        # Drain answers so the socket buffer never fills.
        while select.select([sock], [], [], 0)[0]:
            sock.recv(4096)
        i += 1
        if i % 60 == 0:
            log(f"t={t:.0f}s iteration {i}")
        time.sleep(max(0.0, 1.0 - (time.monotonic() - tick)))


if __name__ == "__main__":
    sys.exit(main())
