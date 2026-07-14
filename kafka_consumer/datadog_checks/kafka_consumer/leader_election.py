# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import threading
import time

from confluent_kafka.error import KafkaError

from datadog_checks.kafka_consumer.constants import LEADER_ELECTION_GROUP_ID, LEADER_ELECTION_TOPIC

HEARTBEAT_TICK_SECONDS = 5


class LeaderElection:
    """Elects a single collector among check instances pointed at the same Kafka cluster.

    Relies on the broker's own consumer-group rebalance protocol: a single-partition
    coordination topic is only ever assigned to one group member at a time. A persistent
    log of "last collected at T" messages on that partition gives a freshly elected
    leader (e.g. after a failover) shared memory of collection cadence, so a failover
    never causes a burst of back-to-back collections.
    """

    def __init__(self, check, client, config, log):
        self.check = check
        self.client = client
        self.config = config
        self.log = log
        self._consumer = None
        self._producer = None
        self._pending_commit_message = None
        self._collecting_this_round = False
        self._stop_heartbeat = None
        self._heartbeat_thread = None

    def _ensure_clients(self):
        if self._consumer is None:
            self.client.ensure_topic(LEADER_ELECTION_TOPIC, num_partitions=1)
            self._consumer = self.client.build_election_consumer(LEADER_ELECTION_GROUP_ID)
            self._consumer.subscribe([LEADER_ELECTION_TOPIC])
        if self._producer is None:
            self._producer = self.client.build_election_producer()

    def should_collect(self):
        """Decide, via the coordination topic, whether this instance should collect this round."""
        self._pending_commit_message = None
        self._collecting_this_round = False
        try:
            self._ensure_clients()
            message = self._consumer.poll(timeout=self.config._request_timeout)
        except Exception:
            self.log.exception("Leader election failed; skipping collection this round.")
            self._submit_is_leader(False)
            return False

        if message is None:
            # No partition assignment yet (still joining/rebalancing) - stand down conservatively.
            self._submit_is_leader(False)
            return False

        error = message.error()
        if error is not None:
            if error.code() == KafkaError._PARTITION_EOF:
                # Caught up with nothing ever written: nobody has collected yet, so we should.
                self._collecting_this_round = True
                self._submit_is_leader(True)
                return True
            self.log.warning("Leader election poll error: %s; skipping collection this round.", error)
            self._submit_is_leader(False)
            return False

        try:
            payload = json.loads(message.value())
            last_collected_at = float(payload["timestamp"])
        except (TypeError, ValueError, KeyError) as e:
            self.log.warning("Unreadable leader election message, treating it as stale: %s", e)
            last_collected_at = 0.0

        if time.time() - last_collected_at < self.config._auto_load_distribution_interval:
            # Someone else collected recently enough; don't commit so a takeover leader
            # still sees this message and re-evaluates its own staleness.
            self._submit_is_leader(False)
            return False

        self._pending_commit_message = message
        self._collecting_this_round = True
        self._submit_is_leader(True)
        return True

    def start_heartbeat(self):
        """Keep polling in the background so a slow collection can't exceed max.poll.interval.ms."""
        if not self._collecting_this_round:
            return
        self._stop_heartbeat = threading.Event()

        def _tick():
            while not self._stop_heartbeat.wait(HEARTBEAT_TICK_SECONDS):
                try:
                    self._consumer.poll(0)
                except Exception:
                    self.log.exception("Leader election heartbeat poll failed.")

        self._heartbeat_thread = threading.Thread(target=_tick, daemon=True)
        self._heartbeat_thread.start()

    def finish(self):
        """Stop the heartbeat, publish a fresh timestamp, and commit the message that triggered this round."""
        if not self._collecting_this_round:
            return
        if self._stop_heartbeat is not None:
            self._stop_heartbeat.set()
            self._heartbeat_thread.join()
            self._stop_heartbeat = None
            self._heartbeat_thread = None

        try:
            self._producer.produce(LEADER_ELECTION_TOPIC, json.dumps({"timestamp": time.time()}).encode())
            self._producer.flush(self.config._request_timeout)
            if self._pending_commit_message is not None:
                self._consumer.commit(message=self._pending_commit_message, asynchronous=False)
        except Exception:
            self.log.exception("Failed to finalize leader election heartbeat.")
        finally:
            self._pending_commit_message = None
            self._collecting_this_round = False

    def _submit_is_leader(self, is_leader):
        self.check.gauge('leader_election.is_leader', int(is_leader), tags=list(self.config._custom_tags))
