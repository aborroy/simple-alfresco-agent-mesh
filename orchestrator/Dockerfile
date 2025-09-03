# ===== Runtime image ==========================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (optional but useful for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
# Pin to reasonable recent versions; adjust if you already have constraints.
RUN pip install --no-cache-dir \
    fastmcp \
    langgraph

WORKDIR /app
COPY router_server.py /app/router_server.py

# Defaults for HTTP mode; override via compose/env if you want stdio
ENV TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8085 \
    AUDIT_MCP_URL=http://alfresco-mcp-audit:8081/mcp \
    DOCS_MCP_URL=http://alfresco-mcp-server:8003/mcp \
    ROUTER_NAME=alfresco-router

EXPOSE 8085
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/router_server.py"]
