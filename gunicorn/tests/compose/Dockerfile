FROM python:alpine
ARG PROC_NAME
ENV proc_name_env=${PROC_NAME}
RUN apk add --no-cache g++
RUN pip install gunicorn setproctitle
COPY app.py /dummy_app.py

EXPOSE 18000
CMD gunicorn -w 2 --bind 0.0.0.0:18000 --name ${proc_name_env} dummy_app:app
