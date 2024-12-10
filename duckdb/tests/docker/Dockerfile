# Use the official DuckDB image as the base image
FROM datacatering/duckdb:v1.1.3

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    curl \
    && apt-get clean

# Install DuckDB CLI using precompiled binary as the pip one is not working
RUN curl -L https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-aarch64.zip -o duckdb.zip && \
    unzip duckdb.zip && \
    mv duckdb /usr/local/bin/duckdb && \
    rm -f duckdb.zip

# Set the default working directory
WORKDIR /data

# Set the entrypoint (this can be a Python script, or you can keep it running)
CMD ["tail", "-f", "/dev/null"]

