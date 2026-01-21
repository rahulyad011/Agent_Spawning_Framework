from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import datetime as dt
import httpx
import pandas as pd


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
class FileReadTool:
    """Read content from uploaded files."""

    name: str = "file_read"
    description: str = "Read the content of an uploaded file. Input: {filename: string}."

    session_uploads_dir: Optional[Path] = None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        filename = input.get("filename")
        if not filename:
            return {"error": "Missing 'filename'."}

        if not self.session_uploads_dir:
            return {"error": "Session uploads directory not set."}

        file_path = self.session_uploads_dir / "files" / filename
        if not file_path.exists():
            return {"error": f"File '{filename}' not found."}

        try:
            # Try text files first
            if file_path.suffix in [".txt", ".md", ".py", ".json", ".csv", ".log"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {"filename": filename, "content": content, "type": "text"}

            # Handle CSV files
            elif file_path.suffix == ".csv":
                df = pd.read_csv(file_path)
                return {
                    "filename": filename,
                    "content": df.to_string(),
                    "type": "csv",
                    "shape": list(df.shape),
                    "columns": list(df.columns),
                }

            # Handle JSON files
            elif file_path.suffix == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    import json

                    data = json.load(f)
                return {
                    "filename": filename,
                    "content": json.dumps(data, indent=2),
                    "type": "json",
                }

            else:
                return {"error": f"Unsupported file type: {file_path.suffix}"}

        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}


@dataclass
class FileListTool:
    """List files uploaded in the current session."""

    name: str = "file_list"
    description: str = "List all files uploaded in the current session."

    session_files: Optional[List[Dict[str, Any]]] = None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_files:
            return {"files": []}

        file_list = [
            {
                "filename": f.get("filename", "unknown"),
                "file_type": f.get("file_type", "unknown"),
                "size_bytes": f.get("size_bytes", 0),
            }
            for f in self.session_files
        ]

        return {"files": file_list, "count": len(file_list)}


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
