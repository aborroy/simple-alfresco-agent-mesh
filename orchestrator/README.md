# MCP Orchestrator

This module provides a *Python-based router MCP server*, created to handle orchestration between *Audit MCP* and *Docs MCP* services

## Quick start

```bash
docker compose up -d
docker compose ps
# stop
docker compose down
```

## Contents

```
orchestrator/
├── Dockerfile         # Container build for the orchestrator
├── compose.yaml       # Compose service definition
├── requirements.txt   # Python dependencies
└── router_server.py   # Routing MCP server implementation
```

## Features

* Routing logic: `router_server.py` uses **LangGraph** to classify requests and decide whether they should go to *Audit MCP* or *Docs MCP*
* Transport: runs over *Streamable HTTP*, making it compatible with modern MCP clients
* Dockerized: includes `Dockerfile` and `compose.yaml` for containerized deployment

## How it fits in the full stack

* Client: sends requests to the Orchestrator
* Orchestrator: classifies and forwards requests to either *Audit MCP* or *Docs MCP*
* Audit MCP / Docs MCP: perform specialized operations and return results
* Orchestrator: sends responses back to the client

See the [root stack README](../README.md) for the full system context
