ARG AIRFLOW_VERSION

FROM apache/airflow:$AIRFLOW_VERSION
USER root
# INSTALL TOOLS
RUN apt-get update \
&& apt-get -y install libaio-dev postgresql-client
RUN mkdir extra
USER airflow
# ENTRYPOINT SCRIPT
COPY ./init.sh ./init.sh
ENTRYPOINT ["./init.sh"]
