#!/bin/bash

set -ex

# VALIDATION ONLY: fault injection for the apt-get update timeout and retry
case "${TARGET_ENV}" in
  py3.13-linux-odbc-2019-single)
    # The first two `apt-get update` calls hang, later calls run the real apt-get
    sudo tee /usr/local/sbin/apt-get > /dev/null <<'EOF'
#!/bin/bash
if [ "$1" = "update" ]; then
  n=$(cat /tmp/fake-apt-update-count 2>/dev/null || echo 0)
  n=$((n + 1))
  echo "$n" > /tmp/fake-apt-update-count
  if [ "$n" -le 2 ]; then
    echo "INJECTED: fake apt-get update call $n hangs at $(date -u +%T)"
    exec sleep 3600
  fi
  echo "INJECTED: fake apt-get update call $n runs the real apt-get at $(date -u +%T)"
fi
exec /usr/bin/apt-get "$@"
EOF
    sudo chmod +x /usr/local/sbin/apt-get
    sudo sh -c 'command -v apt-get'
    ;;
  py3.13-linux-odbc-2019-ha)
    # Stalled mirror: the real apt-get talks to a local server that answers and then sends one byte every 5 s
    nohup python3 -c '
import socket, threading, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8099))
s.listen(16)
def handle(c):
    try:
        c.recv(65536)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 1000000\r\n\r\n")
        while True:
            time.sleep(5)
            c.sendall(b"x")
    except Exception:
        pass
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
' > /tmp/stall-server.log 2>&1 &
    sleep 2
    echo "deb [trusted=yes] http://127.0.0.1:8099/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/stalled-mirror.list
    ;;
esac
date -u +%T

# A stalled package mirror can hang apt-get update until the step times out, so bound and retry it
for attempt in 1 2 3; do
  if sudo timeout 300 apt-get update; then
    break
  fi
  date -u +%T
  if [ "$attempt" -eq 3 ]; then
    exit 1
  fi
  sleep 10
done
date -u +%T
sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev

# Install the Microsoft ODBC driver for SQL Server (Linux)
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18=18.3.3.1-1

set +ex
