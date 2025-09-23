ARG AIRFLOW_VERSION

FROM apache/airflow:$AIRFLOW_VERSION
USER root
# INSTALL TOOLS
RUN rm -f /etc/apt/sources.list.d/mysql.list  # Their certificates expired and we don't really need them
RUN apt-get update
RUN apt-get -y install libaio-dev postgresql-client
RUN mkdir extra
USER airflow
# ENTRYPOINT SCRIPT
COPY ./init.sh ./init.sh
ENTRYPOINT ["./init.sh"]
