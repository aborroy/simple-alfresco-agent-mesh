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

## How the router works

The router is a **tiny FastMCP server** that **proxies tools** from two backends (namespaced) and uses a **LangGraph `StateGraph`** to decide where to send each request

Key ideas from `orchestrator/router_server.py`:

1. Backends and namespaces

   * Two backends are registered: `audit` and `docs`
   * When proxied, tools are **prefixed** (e.g., `audit_getEvents`, `docs_findDocument`), making discovery & filtering trivial

2. Lightweight classifier (regex + heuristics)

   * Regex patterns score the prompt toward one backend:
     * Audit patterns: look for verbs/phrases like *“who deleted/modified”*, *“show activities/logs”*, *“permission changed”*, *“login/logout”*, *“compliance report”*, etc.
     * Docs patterns: look for *“find/search document/file”*, *“download/upload/share”*, *“generate rendition/preview”*, *“metadata/properties of”*, *“list documents/folders”*, etc.
   * Question indicators** bias routing:
     * `who`, `when` > often audit
     * `where`, `how` > often docs
     * `what`, `why` > neutral
   * Fallback heuristics if nothing matches strongly:
     * Length: longer queries lean *docs* (content search/exploration)
     * Action verbs: `show/list/get` > *audit*; `find/search/locate` > *docs*

   The classifier returns a structured result: `{guess: "audit"|"docs", confidence, reason, matched_patterns[]}`. The router attaches this to the MCP trace for debugging

3. LangGraph flow

   * Graph nodes: `START > classify > (audit|docs) > END`
   * The *classify* node runs the regex/heuristics, chooses a *target namespace*, and the *delegate* node forwards to the matching backend (via FastMCP proxy)
   * If confidence is low (or a backend is down), the router can fall back or surface an actionable error

4. Tooling for introspection

   * `list_backend_tools`: lists all proxied tool names by backend
   * `which_backend`: shows which URLs the router is pointing to

Example prompts and likely routing:

```
[DOCS]

> I need to search for documents in Alfresco. Can you search for:
- Documents containing "budget"
- Maximum 5 results

[AUDIT]

> List Alfresco audit apps
> List Alfresco audit entries for audit app "search"
```

## How it fits in the full stack

* Client: sends requests to the Orchestrator
* Orchestrator: classifies and forwards requests to either *Audit MCP* or *Docs MCP*
* Audit MCP / Docs MCP: perform specialized operations and return results
* Orchestrator: sends responses back to the client

See the [root stack README](../README.md) for the full system context
