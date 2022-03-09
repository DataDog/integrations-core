# This script makes the necessary setup to install the Teradata ODBC driver and the Teradata JDBC driver on the agent

ODBC_DRIVER_URL="https://downloads.teradata.com/download/cdn/connectivity/odbc/17.10.x.x/tdodbc1710__ubuntu_x8664.17.10.00.15-1.tar.gz"


JDBC_DRIVER_URL="https://downloads.teradata.com/download/cdn/connectivity/jdbc/17.10.00.27/TeraJDBC__indep_indep.17.10.00.27.tar"

apt-get update

curl -LO $ODBC_DRIVER_URL \
  && tar -xzf tdodbc1710__ubuntu_x8664.17.10.00.15-1.tar.gz \
  && dpkg -i tdodbc1710/tdodbc1710-17.10.00.15-1.x86_64.deb

curl -LO $JDBC_DRIVER_URL \
  && tar -xf TeraJDBC__indep_indep.17.10.00.27.tar
