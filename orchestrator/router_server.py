#!/usr/bin/env python3
import os
from typing import Literal, TypedDict, Dict, Any, List

# FastMCP: tiny MCP server framework with proxy/composition helpers
from fastmcp import FastMCP

# LangGraph for the simple keyword-based router (deterministic & debuggable)
from langgraph.graph import StateGraph, START, END


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
AUDIT_MCP_URL = os.getenv("AUDIT_MCP_URL", "http://localhost:8081/mcp")
DOCS_MCP_URL  = os.getenv("DOCS_MCP_URL",  "http://localhost:8003/mcp")
ROUTER_NAME   = os.getenv("ROUTER_NAME",   "alfresco-router")
TRANSPORT     = os.getenv("TRANSPORT",     "stdio").lower()  # "stdio" | "streamable-http"
HOST          = os.getenv("HOST",          "0.0.0.0")
PORT          = int(os.getenv("PORT",      "8085"))

# Prefixes for namespacing the proxied tool/resource names
AUDIT_NS = "audit"
DOCS_NS  = "docs"


# -----------------------------------------------------------------------------
# Build an MCP proxy that mounts both remote backends with prefixes
# -----------------------------------------------------------------------------
# FastMCP will mirror tools and resources with the prefixes. E.g.:
#   - audit_* tools and audit:// resources
#   - docs_*  tools and docs://  resources
multi_cfg = {
    "mcpServers": {
        AUDIT_NS: {"url": AUDIT_MCP_URL, "transport": "http"},
        DOCS_NS:  {"url": DOCS_MCP_URL,  "transport": "http"},
    }
}

mcp = FastMCP.as_proxy(multi_cfg, name=ROUTER_NAME)


# -----------------------------------------------------------------------------
# LangGraph router: decide audit vs docs from a natural-language prompt
# -----------------------------------------------------------------------------
class RouteState(TypedDict):
    prompt: str
    guess: Literal["audit", "docs"]
    reason: str

# Lightweight, transparent keyword heuristics. Easy to extend later.
AUDIT_HITS: tuple = (
    "audit", "auditing", "activity", "trail", "event", "events", "log", "logs",
    "who", "when", "login", "access", "permission", "permissions", "acl",
    "deleted", "deletion", "modified", "update", "updated", "history",
)
DOCS_HITS: tuple = (
    "site", "sites", "document", "documents", "doc", "file", "files", "folder", "content",
    "node", "nodes", "metadata", "search", "query", "tag", "category",
    "download", "upload", "transform", "rendition", "site", "title", "path",
)

def _classify(state: RouteState) -> RouteState:
    text = state["prompt"].lower()
    s_a = sum(1 for k in AUDIT_HITS if k in text)
    s_d = sum(1 for k in DOCS_HITS if k in text)

    # Tie-breaker: default to docs (more generic workflows)
    guess: Literal["audit", "docs"] = "audit" if s_a > s_d else "docs"
    why = f"Matched {s_a} audit keywords vs {s_d} docs keywords"
    return {"prompt": state["prompt"], "guess": guess, "reason": why}

graph = StateGraph(RouteState)
graph.add_node("classify", _classify)
graph.add_edge(START, "classify")
graph.add_edge("classify", END)
router_graph = graph.compile()


# -----------------------------------------------------------------------------
# Router tool: advisory dispatch (lets the client pick the right namespace)
# -----------------------------------------------------------------------------
@mcp.tool(
    name="route_alfresco",
    description=(
        "Given a natural-language request about Alfresco, decide which backend MCP "
        "to use: 'audit' or 'docs'. Returns a JSON with 'guess' and 'reason'. "
        "Then call the appropriate namespaced tool (audit_* or docs_*)."
    ),
)
def route_alfresco(prompt: str) -> Dict[str, Any]:
    """
    Examples:
      - 'Who deleted file X last week?'           -> audit
      - 'Find invoices from July tagged finance'  -> docs
      - 'Show login activity for user alice'      -> audit
      - 'Generate a rendition for /Sites/sales'   -> docs
    """
    res = router_graph.invoke({"prompt": prompt, "guess": "docs", "reason": ""})
    return {"guess": res["guess"], "reason": res["reason"]}


# -----------------------------------------------------------------------------
# Optional: Introspection helpers (handy for debugging in mcp-cli)
# -----------------------------------------------------------------------------
@mcp.tool(
    name="list_backend_tools",
    description="List all proxied tool names grouped by backend (audit, docs)."
)
def list_backend_tools() -> Dict[str, List[str]]:
    tools = mcp.list_tools()
    audit_tools = [t.name for t in tools if t.name.startswith(f"{AUDIT_NS}_")]
    docs_tools  = [t.name for t in tools if t.name.startswith(f"{DOCS_NS}_")]
    return {"audit": sorted(audit_tools), "docs": sorted(docs_tools)}


@mcp.tool(
    name="which_backend",
    description="Echo which backend URL is configured for 'audit' and 'docs'."
)
def which_backend() -> Dict[str, str]:
    return {"audit": AUDIT_MCP_URL, "docs": DOCS_MCP_URL}


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if TRANSPORT in ("http", "streamable-http"):
        # Prefer Streamable HTTP (new standard). Path is /mcp by FastMCP default
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
    else:
        # STDIO mode for local mcp-cli use
        mcp.run()
