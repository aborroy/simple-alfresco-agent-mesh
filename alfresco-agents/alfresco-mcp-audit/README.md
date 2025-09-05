# Alfresco MCP – Audit

This module provides a *specialized MCP server for Alfresco audit operations*, packaged with Docker for easy startup

> **Credit:** Based on the original project [jottley/alfresco-mcp](https://github.com/jottley/alfresco-mcp).

## Quick start

```bash
docker compose up -d
docker compose ps
# stop
docker compose down
```

## Contents

```
alfresco-mcp-audit/
├── Dockerfile      # Builds the Audit MCP service
├── pom.xml         # Maven configuration
└── compose.yaml    # Compose setup to run this service
```

## Main changes from the original project

* Transport upgrade: updated Java dependencies to support **Streamable HTTP** connections (not available in Spring AI 1.0.1)
* Web transport: uses `spring-ai-starter-mcp-server-webmvc` + `spring-boot-starter-web` instead of `stdio`
* Dockerized: added `Dockerfile` and `compose.yaml` for one-command bring-up

## How it fits in the full stack

This Audit MCP service is designed to be part of a larger Alfresco + MCP deployment

* Alfresco Repository (ACS) provides the content and audit data
* Audit MCP (this service) exposes audit-related operations over MCP using **Streamable HTTP**
* Router MCP orchestrates between multiple MCP services (e.g., Audit MCP, Docs MCP)
* MCP Client connects through the router and can invoke audit operations when needed

See the [root stack README](../README.md) for details on how this service integrates with the rest of the system