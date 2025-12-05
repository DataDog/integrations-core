FROM docker.n8n.io/n8nio/n8n:${N8N_VERSION}

# Set environment variables to enable metrics and logging
ENV N8N_METRICS=true \
    N8N_LOG_LEVEL=debug \
    N8N_METRICS_INCLUDE_DEFAULT_METRICS=true \
    N8N_METRICS_INCLUDE_CACHE_METRICS=true \
    N8N_METRICS_INCLUDE_MESSAGE_EVENT_BUS_METRICS=true \
    N8N_HOST=0.0.0.0 \
    N8N_PORT=5678

# Expose the n8n port
EXPOSE 5678
