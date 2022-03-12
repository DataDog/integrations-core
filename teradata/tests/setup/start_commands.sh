# This script makes the necessary setup to install the Teradata JDBC driver on the agent

JDBC_DRIVER_URL="https://downloads.teradata.com/download/cdn/connectivity/jdbc/17.10.00.27/TeraJDBC__indep_indep.17.10.00.27.tar"

apt-get update

curl -LO $JDBC_DRIVER_URL \
  && tar -xf TeraJDBC__indep_indep.17.10.00.27.tar
