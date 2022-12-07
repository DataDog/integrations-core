FROM apache/airflow:2.1.4-python3.8
USER root
# INSTALL TOOLS
RUN apt-get update \
&& apt-get -y install libaio-dev \
&& apt-get install postgresql-client
RUN mkdir extra
USER airflow
# ENTRYPOINT SCRIPT
COPY ./init.sh ./init.sh
ENTRYPOINT ["./init.sh"]
