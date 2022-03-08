# This script makes the necessary setup to install the Teradata ODBC driver on the agent

DRIVER_URL="https://downloads.teradata.com/download/cdn/connectivity/odbc/17.10.x.x/tdodbc1710__ubuntu_x8664.17.10.00.15-1.tar.gz"

apt-get update

curl -LO $DRIVER_URL \
  && tar -xzf tdodbc1710__ubuntu_x8664.17.10.00.15-1.tar.gz \
  && dpkg -i tdodbc1710/tdodbc1710-17.10.00.15-1.x86_64.deb
