FROM python:3.11.1-slim

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir temporalio==1.0.0
COPY run_worker.py /run_worker.py

CMD ["/run_worker.py"]
ENTRYPOINT ["python"]