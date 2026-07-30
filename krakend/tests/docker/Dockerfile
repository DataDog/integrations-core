FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY api.py /app/api.py

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt

# Run the application
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]