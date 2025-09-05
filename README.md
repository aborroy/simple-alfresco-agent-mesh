# Simple Alfresco Agent Mesh

A hands-on lab to compare three routing options (**cagent**, **LangGraph**, **LlamaIndex**) over the same Alfresco setup

The **mcp-client** always talks to MCP Server available in `localhost:8085`; one router is enabled at a time, which then fans out to **MCP Audit** and **MCP Docs**, both talking to the **Alfresco Repository**

The stack that spins up:

* Alfresco Community Repository including Audit sample configuration
* Two MCP servers:
  * Audit MCP
    * Spring AI, streamable HTTP (exposes audit-centric tools)
    * Source code available in https://github.com/jottley/alfresco-mcp
  * Docs MCP
    * Python `alfresco-mcp` server (content/doc tools)
    * Source code available in https://github.com/stevereiner/python-alfresco-mcp-server
* An MCP Router/Orchestrator (cagent, LangGraph or LlamaIndex): service that classifies the user prompt and forwards the MCP call to the right backend (*audit* vs *docs*)

Designed to be easy to run locally, easy to understand, and a good template for building more sophisticated Agent Meshes


## What’s inside

```

.
├── agent-mesh-tools
│   ├── cagent/               # Router with Docker cagent (LLM required)
│   ├── langgraph/            # Router with LangGraph (deterministic, no LLM)
│   └── llamaindex/           # Router with LlamaIndex (LLM required)
├── alfresco-agents
│   ├── alfresco/             # Alfresco Community stack (Repo, Share, Search, etc.)
│   ├── alfresco-mcp-audit/   # MCP Audit server
│   ├── alfresco-mcp-server/  # MCP Docs server
│   └── compose.yaml          # Always-on: Repo + MCP backends
├── mcp-client/               # Client used to test the active router
└── compose.yaml              # Root compose with `include:` and profiles per router

````

## Architecture

```mermaid
flowchart LR
  %% Client
  C[mcp-client]

  %% Routers
  subgraph Routers
    CA[cagent - router:8085]
    LG[langgraph - router:8085]
    LI[llamaindex - router:8085]
  end

  %% MCP backends
  subgraph MCP["MCP Servers"]
    AU[MCP Audit - 8081]
    DO[MCP Docs - 8003]
  end

  %% Alfresco core
  subgraph Alfresco
    RE[Alfresco Repository - 8080]
  end

  %% Connections
  C --> CA
  C --> LG
  C --> LI

  CA --> AU
  CA --> DO
  LG --> AU
  LG --> DO
  LI --> AU
  LI --> DO

  AU --> RE
  DO --> RE
````

* The **Router** is the single MCP endpoint for clients
* It *classifies* each request and *delegates* to either the **Audit MCP** or **Docs MCP** backend over Streamable HTTP
* Both backends talk to **Alfresco**

## Routers at a glance (pick one)

* **LangGraph** — *deterministic router, no LLM required*. Great for repeatable flows and simple, auditable routing rules.
* **LlamaIndex** — *LLM-driven tool routing*. Uses the model to choose between Audit/Docs tools; more adaptive, needs an LLM.
* **cagent** — *LLM-driven agent runtime (YAML)* with first-class MCP tool integration. It runs standalone as a CLI/TUI agent, as described in [Instantly Build AI Agents for Alfresco with Docker new "cagent"](https://connect.hyland.com/t5/alfresco-blog/instantly-build-ai-agents-for-alfresco-with-docker-new-quot/ba-p/492609)

## Requirements

- Docker & Docker Compose v2+
  Needed to run the full stack (Alfresco, MCP servers, routers, client).

- System resources
  At least 8 GB RAM free and 4 CPU cores recommended.

- Open ports
  - 8080 > Alfresco Repository  
  - 8081 > MCP Audit  
  - 8003 > MCP Docs  
  - 8085 > Active router (LangGraph, or LlamaIndex)

- LLM runtime
  - For `cagent` and LlamaIndex, an LLM is required
  - This lab uses [Ollama](https://ollama.ai/) with the local model `gpt-oss`
  - Ensure Ollama is installed and the model is pulled before starting:
    ```bash
    ollama pull gpt-oss
    ```

- No LLM required
  - LangGraph router works deterministically without an LLM

## Quick start

1. Start Alfresco Community + MCP backends

```bash
docker compose up --build
```

2. Activate exactly one router (both expose `:8085`):

```bash
docker compose --profile langgraph up -d
```

```bash
docker compose --profile llamaindex up -d
```

> For `cagent` follow the steps in [Instantly Build AI Agents for Alfresco with Docker new "cagent"](https://connect.hyland.com/t5/alfresco-blog/instantly-build-ai-agents-for-alfresco-with-docker-new-quot/ba-p/492609)

3. Test with the client (always hits 8085)

```bash
docker compose -f mcp-client/compose.yaml run --rm mcp-client
```

4. Switch routers (keep Alfresco running)

```bash
docker compose --profile langgraph down
docker compose --profile llamaindex up --build
```

## Example prompts (copy/paste)

### \[DOCS]

> I need to search for documents in Alfresco. Can you search for:
>
> * Documents containing "budget"
> * Maximum 5 results

### \[AUDIT]

> List Alfresco audit apps
> List Alfresco audit entries for audit app "search"

Tips:

* If your router is *LangGraph*, routing is rule-based—logs/retention/compliance > **Audit**; search/metadata/renditions/transforms > **Docs**
* If it’s *LlamaIndex* or *cagent*, ensure a model is configured (e.g., OpenAI/Anthropic/Gemini or a local model via Docker Model Runner)

## Lab flow (recommended)

1. Bring up Alfresco + MCP (wait for health)
2. Start LangGraph first (no keys needed) and run the prompts above
3. Stop LangGraph, start LlamaIndex; repeat the prompts and observe differences in routing/answers
4. Stop LlamaIndex, follow the steps in [Instantly Build AI Agents for Alfresco with Docker new "cagent"](https://connect.hyland.com/t5/alfresco-blog/instantly-build-ai-agents-for-alfresco-with-docker-new-quot/ba-p/492609)


## License

This repository is provided under the **Apache 2.0** license (see `LICENSE`).
Upstream components maintain their own licenses.