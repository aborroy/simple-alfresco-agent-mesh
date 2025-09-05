FROM python:3.11-slim AS base

ARG APP_FILE=router_server.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal OS deps + tini for clean PID 1
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl tini \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user
RUN useradd -m -u 10001 appuser
WORKDIR /app
COPY ${APP_FILE} /app/app.py
RUN chown -R appuser:appuser /app
USER appuser

# Defaults (override via -e)
ENV TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8085 \
    ROUTER_NAME=alfresco-router \
    AUDIT_MCP_URL=http://localhost:8081/mcp \
    DOCS_MCP_URL=http://localhost:8003/mcp

EXPOSE 8085

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/app.py"]
