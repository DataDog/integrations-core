#!/usr/bin/env python3
"""Drive rabbitmq-full so the rabbitmq check and the OTel rabbitmqreceiver report
their full metric surface with non-trivial values.

perf-test (a sibling container) already drives the raw publish/consume/ack rates.
This sidecar covers what perf-test does not:

  * durable queues + persistent messages   -> node.msg_store_*, node.queue_index_*
  * queue/exchange declare + delete churn   -> node.queue_created/declared/deleted
  * connection + channel open/close churn   -> node.connection_*, node.channel_*
  * unroutable publishes                     -> message.dropped / *unroutable*
  * messages left ready and left unacked     -> message.current {ready, unacknowledged}

Consumes DB_HOST / AMQP_PORT / RABBITMQ_USER / RABBITMQ_PASSWORD from the fixture.
Set ACTIVITY_GEN=0 to keep the container up but idle (a quiescent rabbitmq-full).
"""
import os
import sys
import time
import threading

import pika

HOST = os.environ.get("DB_HOST", "rabbitmq")
PORT = int(os.environ.get("AMQP_PORT", "5672"))
USER = os.environ.get("RABBITMQ_USER", "guest")
PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")
INTERVAL = float(os.environ.get("ACTIVITY_INTERVAL", "5"))  # seconds between cycles
WINDOW = int(os.environ.get("ACTIVITY_QUEUE_WINDOW", "5"))  # durable queues kept alive
UNACKED_PREFETCH = int(os.environ.get("ACTIVITY_UNACKED", "20"))

EXCHANGE = "activity.direct"
ROUTING_KEY = "activity.rk"
UNROUTABLE_KEY = "activity.no-binding"
UNACKED_QUEUE = "activity.unacked"

PERSISTENT = pika.BasicProperties(delivery_mode=2)


def log(msg):
    print(f"activity-gen: {msg}", flush=True)


def conn_params():
    return pika.ConnectionParameters(
        host=HOST,
        port=PORT,
        credentials=pika.PlainCredentials(USER, PASSWORD),
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=1,
        socket_timeout=10,
    )


def wait_for_broker(timeout=180):
    """Block until the broker accepts a connection, or exit non-zero."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            pika.BlockingConnection(conn_params()).close()
            log("broker is up")
            return
        except Exception as exc:  # noqa: BLE001 - startup probe, any failure means "not ready yet"
            log(f"waiting for broker ({exc.__class__.__name__})...")
            time.sleep(3)
    log("broker never became reachable; exiting")
    sys.exit(1)


def unacked_holder():
    """Keep a pool of messages permanently unacknowledged so
    message.current{state=unacknowledged} stays non-zero. Consumes with a
    prefetch window and never acks; auto-reconnects on failure."""
    while True:
        try:
            conn = pika.BlockingConnection(conn_params())
            ch = conn.channel()
            ch.queue_declare(queue=UNACKED_QUEUE, durable=True)
            ch.basic_qos(prefetch_count=UNACKED_PREFETCH)
            # Seed the queue so there is something to hold unacked.
            for n in range(UNACKED_PREFETCH * 2):
                ch.basic_publish("", UNACKED_QUEUE, f"unacked-{n}".encode(), PERSISTENT)
            ch.basic_consume(UNACKED_QUEUE, on_message_callback=lambda *a: None, auto_ack=False)
            log("unacked holder attached")
            ch.start_consuming()  # blocks, holding delivered messages unacked
        except Exception as exc:  # noqa: BLE001
            log(f"unacked holder reconnecting ({exc.__class__.__name__})")
            time.sleep(5)


def run_cycle(i, live_queues):
    """One churn cycle on its own short-lived connection/channel."""
    conn = pika.BlockingConnection(conn_params())          # connection_created
    ch = conn.channel()                                    # channel_created
    ch.confirm_delivery()

    ch.exchange_declare(EXCHANGE, exchange_type="direct", durable=True)

    # Durable queue with persistent, partly-consumed messages: exercises
    # msg_store / queue_index and leaves some messages "ready".
    qname = f"activity.durable.{i}"
    ch.queue_declare(queue=qname, durable=True)            # queue_declared/created
    ch.queue_bind(qname, EXCHANGE, routing_key=ROUTING_KEY)
    for n in range(40):
        ch.basic_publish(EXCHANGE, ROUTING_KEY, f"msg-{i}-{n}".encode(), PERSISTENT)
    # Consume+ack half (drives acknowledged + msg_store reads); leave the rest ready.
    for _ in range(20):
        method, _props, body = ch.basic_get(qname, auto_ack=False)
        if method is None:
            break
        ch.basic_ack(method.delivery_tag)
    live_queues.append(qname)

    # Unroutable publishes: no binding for this key -> dropped (message.dropped /
    # *unroutable*). mandatory=False so the broker drops rather than returns.
    for n in range(10):
        ch.basic_publish(EXCHANGE, UNROUTABLE_KEY, f"drop-{i}-{n}".encode(), mandatory=False)

    # Ephemeral queue declared and immediately deleted -> queue_created + deleted.
    eph = f"activity.ephemeral.{i}"
    ch.queue_declare(queue=eph, durable=False, auto_delete=False)
    ch.queue_delete(eph)                                   # queue_deleted

    # Bound the number of live durable queues; deleting the oldest drives
    # queue_deleted and keeps the broker from growing without limit.
    while len(live_queues) > WINDOW:
        old = live_queues.pop(0)
        try:
            ch.queue_delete(old)
        except Exception:  # noqa: BLE001 - queue may already be gone
            pass

    ch.close()                                             # channel_closed
    conn.close()                                           # connection_closed


def main():
    if os.environ.get("ACTIVITY_GEN", "1") == "0":
        log("disabled via ACTIVITY_GEN=0; idling")
        while True:
            time.sleep(3600)

    wait_for_broker()

    holder = threading.Thread(target=unacked_holder, daemon=True)
    holder.start()

    live_queues = []
    i = 0
    while True:
        i += 1
        try:
            run_cycle(i, live_queues)
            if i % 10 == 0:
                log(f"completed {i} cycles ({len(live_queues)} durable queues live)")
        except Exception as exc:  # noqa: BLE001 - keep the workload alive across broker blips
            log(f"cycle {i} failed ({exc.__class__.__name__}: {exc}); retrying")
            time.sleep(5)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
