#!/usr/bin/env python3
import os
import re
from typing import Literal, TypedDict, Dict, Any, List, Optional
from dataclasses import dataclass

# FastMCP: tiny MCP server framework with proxy/composition helpers
from fastmcp import FastMCP

# LangGraph for the simple keyword-based router (deterministic & debuggable)
from langgraph.graph import StateGraph, START, END


# Configuration
AUDIT_MCP_URL = os.getenv("AUDIT_MCP_URL", "http://localhost:8081/mcp")
DOCS_MCP_URL  = os.getenv("DOCS_MCP_URL",  "http://localhost:8003/mcp")
ROUTER_NAME   = os.getenv("ROUTER_NAME",   "alfresco-router")
TRANSPORT     = os.getenv("TRANSPORT",     "stdio").lower()  # "stdio" | "streamable-http"
HOST          = os.getenv("HOST",          "0.0.0.0")
PORT          = int(os.getenv("PORT",      "8085"))

# Prefixes for namespacing the proxied tool/resource names
AUDIT_NS = "audit"
DOCS_NS  = "docs"


# Classification System
@dataclass
class ClassificationResult:
    guess: Literal["audit", "docs"]
    confidence: float  # 0.0 to 1.0
    reason: str
    matched_patterns: List[str]

class Classifier:
    def __init__(self):
        # Keyword sets with weights
        self.audit_keywords = {
            # High confidence keywords
            "audit": 3, "auditing": 3, "trail": 3, "activity": 2, "event": 2, "events": 2,
            "log": 2, "logs": 2, "login": 3, "logout": 2, "access": 2, "permission": 2,
            "permissions": 2, "acl": 3, "security": 2, "deleted": 2, "deletion": 2,
            "modified": 2, "update": 1, "updated": 2, "history": 2, "track": 2, "tracking": 2,
            "monitor": 2, "monitoring": 2, "compliance": 3, "violation": 3, "breach": 3,
            "unauthorized": 3, "failed": 2, "attempt": 2, "session": 2, "timestamp": 2,
            # User-related audit terms
            "user": 1, "users": 1, "admin": 2, "administrator": 2, "role": 1, "roles": 1,
            # Temporal audit indicators
            "when": 2, "who": 3, "why": 2, "how": 1, "changed": 2, "created": 1, "removed": 2
        }
        
        self.docs_keywords = {
            # High confidence keywords
            "document": 3, "documents": 3, "doc": 2, "docs": 2, "file": 2, "files": 2,
            "folder": 2, "folders": 2, "content": 2, "site": 2, "sites": 2, "node": 2,
            "nodes": 2, "metadata": 3, "properties": 2, "tag": 2, "tags": 2, "category": 2,
            "search": 2, "query": 2, "find": 1, "download": 2, "upload": 2, "transform": 3,
            "rendition": 3, "preview": 2, "thumbnail": 2, "version": 2, "versions": 2,
            "workflow": 2, "process": 1, "repository": 3, "library": 2, "space": 2,
            # Content operations
            "create": 1, "edit": 1, "move": 1, "copy": 1, "share": 2, "link": 1,
            "export": 2, "import": 2, "sync": 2, "backup": 2, "restore": 2,
            # Content types
            "pdf": 2, "image": 1, "video": 1, "text": 1, "spreadsheet": 2, "presentation": 2
        }
        
        # Intent patterns using regex
        self.audit_patterns = [
            (r"who\s+(deleted|modified|accessed|created|updated)", "user action inquiry", 3),
            (r"when\s+(was|did|were)", "temporal inquiry", 2),
            (r"(show|list|get)\s+(activity|activities|events|logs)", "audit request", 3),
            (r"(track|monitor|audit)\s+", "explicit audit request", 3),
            (r"(login|logout|signin|signout)", "authentication events", 3),
            (r"(permission|access)\s+(denied|granted|changed)", "permission events", 3),
            (r"security\s+(violation|breach|issue)", "security events", 3),
            (r"compliance\s+(report|check|audit)", "compliance inquiry", 3),
        ]
        
        self.docs_patterns = [
            (r"(find|search|locate|get)\s+(document|file|content)", "content search", 3),
            (r"(download|upload|share)\s+", "content operation", 2),
            (r"(create|generate)\s+(rendition|preview|thumbnail)", "content transformation", 3),
            (r"(list|show)\s+(files|documents|folders)", "content listing", 2),
            (r"(move|copy|delete)\s+(to|from|in)\s+", "content management", 2),
            (r"(tag|categorize|label)\s+", "content organization", 2),
            (r"(metadata|properties)\s+(of|for)", "content metadata", 3),
            (r"site\s+(content|documents|files)", "site content", 2),
        ]
        
        # Question type indicators
        self.question_indicators = {
            "who": "audit",      # Usually about user actions
            "when": "audit",     # Usually about timing of actions
            "what": "neutral",   # Could be either
            "where": "docs",     # Usually about content location
            "how": "docs",       # Usually about processes/workflows
            "why": "neutral",    # Context dependent
        }
    
    def classify(self, prompt: str) -> ClassificationResult:
        text = prompt.lower().strip()
        
        # 1. Pattern matching (highest priority)
        audit_pattern_score = 0
        docs_pattern_score = 0
        matched_patterns = []
        
        for pattern, description, weight in self.audit_patterns:
            if re.search(pattern, text):
                audit_pattern_score += weight
                matched_patterns.append(f"audit pattern: {description}")
        
        for pattern, description, weight in self.docs_patterns:
            if re.search(pattern, text):
                docs_pattern_score += weight
                matched_patterns.append(f"docs pattern: {description}")
        
        # 2. Weighted keyword matching
        audit_keyword_score = sum(weight for word, weight in self.audit_keywords.items() if word in text)
        docs_keyword_score = sum(weight for word, weight in self.docs_keywords.items() if word in text)
        
        # 3. Question type analysis
        question_bonus = 0
        first_word = text.split()[0] if text.split() else ""
        if first_word in self.question_indicators:
            if self.question_indicators[first_word] == "audit":
                question_bonus = 1
            elif self.question_indicators[first_word] == "docs":
                question_bonus = -1
        
        # 4. Calculate total scores
        total_audit_score = audit_pattern_score + audit_keyword_score + max(0, question_bonus)
        total_docs_score = docs_pattern_score + docs_keyword_score + max(0, -question_bonus)
        
        # 5. Determine result with confidence
        if total_audit_score == 0 and total_docs_score == 0:
            # No keywords/patterns matched - use fallback heuristics
            return self._fallback_classification(text, matched_patterns)
        
        total_score = total_audit_score + total_docs_score
        
        if total_audit_score > total_docs_score:
            confidence = total_audit_score / total_score if total_score > 0 else 0.5
            guess = "audit"
            reason = f"Audit score: {total_audit_score}, Docs score: {total_docs_score}"
        else:
            confidence = total_docs_score / total_score if total_score > 0 else 0.5
            guess = "docs"
            reason = f"Docs score: {total_docs_score}, Audit score: {total_audit_score}"
        
        # Add pattern information to reason
        if matched_patterns:
            reason += f". Matched: {', '.join(matched_patterns)}"
        
        return ClassificationResult(
            guess=guess,
            confidence=min(confidence, 1.0),
            reason=reason,
            matched_patterns=matched_patterns
        )
    
    def _fallback_classification(self, text: str, matched_patterns: List[str]) -> ClassificationResult:
        """Fallback classification when no keywords/patterns match"""
        
        # Heuristic 1: Length-based (longer queries often about content search)
        if len(text.split()) > 10:
            return ClassificationResult(
                guess="docs",
                confidence=0.6,
                reason="Long query suggests content search (fallback heuristic)",
                matched_patterns=matched_patterns
            )
        
        # Heuristic 2: Presence of specific verbs
        action_verbs_audit = {"show", "list", "get", "tell", "display"}
        action_verbs_docs = {"find", "search", "locate", "retrieve", "fetch"}
        
        words = set(text.split())
        
        if words.intersection(action_verbs_audit):
            return ClassificationResult(
                guess="audit",
                confidence=0.55,
                reason="Contains audit-like action verbs (fallback heuristic)",
                matched_patterns=matched_patterns
            )
        
        if words.intersection(action_verbs_docs):
            return ClassificationResult(
                guess="docs",
                confidence=0.55,
                reason="Contains docs-like action verbs (fallback heuristic)",
                matched_patterns=matched_patterns
            )
        
        # Heuristic 3: Default to docs (as it handles more general cases)
        return ClassificationResult(
            guess="docs",
            confidence=0.5,
            reason="No specific indicators found, defaulting to docs (general content operations)",
            matched_patterns=matched_patterns
        )


# Build an MCP proxy that mounts both remote backends with prefixes
multi_cfg = {
    "mcpServers": {
        AUDIT_NS: {"url": AUDIT_MCP_URL, "transport": "http"},
        DOCS_NS:  {"url": DOCS_MCP_URL,  "transport": "http"},
    }
}

mcp = FastMCP.as_proxy(multi_cfg, name=ROUTER_NAME)

# Initialize the classifier
classifier = Classifier()


# LangGraph router
class RouteState(TypedDict):
    prompt: str
    guess: Literal["audit", "docs"]
    confidence: float
    reason: str
    matched_patterns: List[str]

def _classify(state: RouteState) -> RouteState:
    result = classifier.classify(state["prompt"])
    return {
        "prompt": state["prompt"],
        "guess": result.guess,
        "confidence": result.confidence,
        "reason": result.reason,
        "matched_patterns": result.matched_patterns
    }

graph = StateGraph(RouteState)
graph.add_node("classify", _classify)
graph.add_edge(START, "classify")
graph.add_edge("classify", END)
router_graph = graph.compile()


# Router tool
@mcp.tool(
    name="route_alfresco",
    description=(
        "Given a natural-language request about Alfresco, decide which backend MCP "
        "to use: 'audit' or 'docs'. Returns JSON with 'guess', 'confidence', 'reason', "
        "and 'matched_patterns'. Then call the appropriate namespaced tool (audit_* or docs_*)."
    ),
)
def route_alfresco(prompt: str) -> Dict[str, Any]:
    """
    Routing with confidence scoring and pattern matching.
    
    Examples:
      - 'Who deleted file X last week?'              -> audit (high confidence)
      - 'Find invoices from July tagged finance'     -> docs (high confidence)
      - 'Show me something about user activities'    -> audit (medium confidence)
      - 'I need help with content management'        -> docs (fallback heuristic)
      - 'What happened yesterday?'                    -> audit (question pattern)
    """
    initial_state = {
        "prompt": prompt,
        "guess": "docs",
        "confidence": 0.5,
        "reason": "",
        "matched_patterns": []
    }
    
    result = router_graph.invoke(initial_state)
    
    return {
        "guess": result["guess"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "matched_patterns": result["matched_patterns"]
    }


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


# Entrypoint
if __name__ == "__main__":
    if TRANSPORT in ("http", "streamable-http"):
        # Prefer Streamable HTTP (new standard). Path is /mcp by FastMCP default
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
    else:
        # STDIO mode for local mcp-cli use
        mcp.run()