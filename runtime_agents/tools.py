from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol, runtime_checkable

import datetime as dt
import httpx


@runtime_checkable
class Tool(Protocol):
    name: str
    description: str

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class TimeTool:
    name: str = "time_now"
    description: str = "Return current UTC time in ISO format."

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {"utc_now": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"}


@dataclass
class HttpGetTool:
    name: str = "http_get"
    description: str = "Fetch a URL via HTTP GET. Input: {url: string}."

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        url = input.get("url")
        if not url:
            return {"error": "Missing 'url'."}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            return {"status": r.status_code, "text": r.text[:5000]}


# --- MCP-ready slot ---
@dataclass
class MCPToolAdapter:
    """Placeholder adapter to wrap an MCP tool call.

    In a real implementation, you would:
    - connect to an MCP server (stdio/http)
    - list available tools
    - call the selected tool by name with JSON input

    This starter keeps the interface so you can drop in your MCP client later.
    """

    name: str
    description: str

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "error": "MCPToolAdapter not wired yet.",
            "hint": "Wrap your MCP client here and route tool calls.",
            "tool": self.name,
            "input": input,
        }
