# Use the Python slim image as a base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script and healthcheck script
COPY script.py /app/script.py
COPY healthcheck_script.sh /app/healthcheck_script.sh
