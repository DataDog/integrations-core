FROM python:3.12-slim

RUN pip install --no-cache-dir celery[redis] flower redis

RUN mkdir -p /var/run/celery
RUN mkdir -p /var/log/celery

COPY . .

CMD ["celery", "-A", "tasks", "worker", "--loglevel=DEBUG"]