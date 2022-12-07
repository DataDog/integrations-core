FROM python:3.10-alpine3.16
ARG PROC_NAME
ARG GUNICORN_VERSION
ENV proc_name_env=${PROC_NAME}
ENV gunicorn_version_env=${GUNICORN_VERSION}
RUN apk add --no-cache g++
RUN pip install setproctitle
RUN if [ -z "$gunicorn_version_env" ]; \
    then pip install gunicorn; \
    else pip install gunicorn==${gunicorn_version_env}; \
    fi
COPY app.py /dummy_app.py

EXPOSE 18000
CMD gunicorn -w 4 --bind 0.0.0.0:18000 --name ${proc_name_env} dummy_app:app
