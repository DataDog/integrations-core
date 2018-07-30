FROM datadog/agent:6.4.0-rc.3
ENV DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ENV ACCEPT_EULA=Y

RUN apt-get update && apt-get install -y build-essential unixodbc-dev python-dev
RUN curl -O https://packages.microsoft.com/debian/9/prod/pool/main/m/msodbcsql17/msodbcsql17_17.1.0.1-1_amd64.deb
RUN apt-get install -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confnew ./*.deb

# Install deps since omnibus skips them (because we don't officially support linux yet)
RUN /opt/datadog-agent/embedded/bin/pip install adodbapi==2.6.0.7 pyro4==4.36 testfixtures==4.14.3 serpent==1.23 pyodbc==4.0.13

# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-2017
# https://stackoverflow.com/a/48849351/5854007
# RUN odbcinst -j
# RUN cat /etc/odbcinst.ini
