# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
IBM MQ Connection Simulation Script

This script simulates an active connection to an IBM MQ queue manager for manual testing purposes.
It connects to a specified queue manager, puts a message to a queue, and maintains the connection
for 120 seconds to simulate an active channel connection.

This script was used for manual testing of the IBM MQ integration PR that adds connection-related
metrics (ibm_mq.channel.conn_status and ibm_mq.channel.connections_active). By creating active
connections, we can verify that the new metrics properly detect and count channel connections.

Usage: python simulate_mq_conn.py <QMGR> <CHANNEL> <HOST> <PORT> <QUEUE> [<MESSAGE>] [<USER>] [<PASSWORD>]
Example: python simulate_mq_conn.py QM1 GCP.A localhost 11414 APP.QUEUE.1 "Hello from script" admin passw0rd
"""

import sys
import time

import pymqi

# Usage: python simulate_mq_conn.py <QMGR> <CHANNEL> <HOST> <PORT> <QUEUE> [<MESSAGE>] [<USER>] [<PASSWORD>]
# Example: python simulate_mq_conn.py QM1 GCP.A localhost 11414 APP.QUEUE.1 "Hello from script" admin passw0rd

qmgr_name = sys.argv[1] if len(sys.argv) > 1 else "QM1"
channel = sys.argv[2] if len(sys.argv) > 2 else "DEV.ADMIN.SVRCONN"
host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
port = sys.argv[4] if len(sys.argv) > 4 else "11414"
queue_name = sys.argv[5] if len(sys.argv) > 5 else "APP.QUEUE.1"
message = sys.argv[6] if len(sys.argv) > 6 else "Hello from pymqi!"
user = sys.argv[7] if len(sys.argv) > 7 else "admin"
password = sys.argv[8] if len(sys.argv) > 8 else "passw0rd"

conn_info = f"{host}({port})"

print(f"Connecting to {qmgr_name} on {host}:{port} via channel {channel} as {user}...")

qmgr = pymqi.connect(qmgr_name, channel, conn_info, user, password)
queue = pymqi.Queue(qmgr, queue_name)

print(f"Putting message: {message}")
queue.put(message)

print("Sleeping for 120 seconds to keep the connection open...")
time.sleep(120)

queue.close()
qmgr.disconnect()
print("Connection closed.")
