#!/usr/bin/env python3
import os
import json
import asyncio
from typing import Any, Dict, List

from fastmcp import FastMCP

# LlamaIndex (workflow agents)
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.ollama import Ollama

# ---------------- Config ----------------
AUDIT_MCP_URL = os.getenv("AUDIT_MCP_URL", "http://localhost:8081/mcp")
DOCS_MCP_URL  = os.getenv("DOCS_MCP_URL",  "http://localhost:8003/mcp")
ROUTER_NAME   = os.getenv("ROUTER_NAME",   "alfresco-agent")
TRANSPORT     = os.getenv("TRANSPORT",     "streamable-http").lower()  # "stdio" | "streamable-http"
HOST          = os.getenv("HOST",          "0.0.0.0")
PORT          = int(os.getenv("PORT",      "8085"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gpt-oss")

# ------------- FastMCP proxy -------------
mcp = FastMCP.as_proxy(
    {
        "mcpServers": {
            "audit": {"url": AUDIT_MCP_URL, "transport": "http"},
            "docs":  {"url": DOCS_MCP_URL,  "transport": "http"},
        }
    },
    name=ROUTER_NAME,
)

# ------------- Build LlamaIndex tools from MCP -------------
def build_li_tools() -> List[FunctionTool]:
    mcp_tools = asyncio.run(mcp._list_tools())
    li_tools: List[FunctionTool] = []

    for t in mcp_tools:
        name = t.name
        desc = t.description or f"Invoke MCP tool `{name}`."

        def make_caller(tool_name_local: str):
            def _caller(**kwargs) -> str:
                resp: Dict[str, Any] = asyncio.run(mcp._call_tool(tool_name_local, kwargs or {}))
                return json.dumps(resp, ensure_ascii=False)
            return _caller

        li_tools.append(
            FunctionTool.from_defaults(
                fn=make_caller(name),
                name=name,                # keep audit__* / docs__* for routing
                description=desc,
            )
        )
    return li_tools

LI_TOOLS = build_li_tools()

SYSTEM_PROMPT = """You are an Alfresco helper that decides which MCP tool to call.

Routing:
- audit/logs/retention/compliance > prefer tools starting with 'audit__'
- content/search/metadata/renditions/transforms > prefer 'docs__'

Behavior:
- Pick exactly one best tool and call it with reasonable parameters.
- If you lack required parameters, ask briefly, then call the tool.
- Return the tool's response as-is.
"""

llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=180.0)

AGENT = ReActAgent(
    tools=LI_TOOLS,
    llm=llm,
    system_prompt=SYSTEM_PROMPT,
    verbose=False,
)

# ------------- Expose router as MCP tools -------------
@mcp.tool(
    name="ask_alfresco",
    description="Free-text. ReActAgent selects one audit__* or docs__* tool and calls it.",
)
def ask_alfresco(prompt: str) -> str:
    return str(asyncio.run(AGENT.run(prompt)))

@mcp.tool(
    name="list_available_tools",
    description="List MCP tools exposed to the agent.",
)
def list_available_tools() -> List[str]:
    return [t.metadata.name for t in LI_TOOLS]

# ------------- Run -------------
if __name__ == "__main__":
    if TRANSPORT == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
