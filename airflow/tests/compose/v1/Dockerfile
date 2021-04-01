FROM puckel/docker-airflow:1.10.6

# Need to be root to install pip packages, we will switch back to airflow user later.
USER root

RUN pip install 'apache-airflow[statsd]'

USER airflow
