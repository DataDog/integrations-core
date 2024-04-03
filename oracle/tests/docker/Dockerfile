ARG ORACLE_DATABASE_VERSION

FROM datadog/docker-library:oracle-${ORACLE_DATABASE_VERSION}-slim
COPY ./server/tnsnames.ora /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/tnsnames.ora
COPY ./server/listener.ora /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/listener.ora
COPY ./server/sqlnet.ora /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/sqlnet.ora
COPY ./server/server_wallet /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/server_wallet
USER root

# Give user `oracle` (uid 54321) permission to modify /u01/app/oracle
RUN chown -R 54321:54321 /u01/app/oracle

# Remove permission for user `oracle` to override modified tnsnames.ora, listener.ora, sqlnet.ora
RUN chown root:root /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/tnsnames.ora
RUN chown root:root /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/listener.ora
RUN chown root:root /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/sqlnet.ora
RUN chown root:root /u01/app/oracle/product/12.2.0/dbhome_1/admin/InfraDB/server_wallet

# If you need to regenerate the keys, uncomment this and run the script in the README from the test folder
# RUN yum -y install java

USER oracle
