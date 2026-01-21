"""Shared tool registry for all agent architectures."""

from pathlib import Path
from typing import Dict, Optional

from runtime_agents.shared.tools import (
    FileListTool,
    FileReadTool,
    HttpGetTool,
    TimeTool,
)
from runtime_agents.shared.db_tools import (
    DatabaseConnectionTool,
    DatabaseQueryTool,
    SchemaIntrospectionTool,
)
from runtime_agents.shared.image_tools import ImageAnalysisTool, ImageListTool


class ToolRegistry:
    """Registry for managing tools across all agent architectures."""

    def __init__(self):
        self._tools: Dict[str, object] = {}

    def register_tool(self, name: str, tool: object) -> None:
        """Register a tool."""
        self._tools[name] = tool

    def get_tool(self, name: str) -> Optional[object]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> Dict[str, object]:
        """Get all registered tools."""
        return self._tools.copy()

    def list_tool_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


def get_default_tools(
    session_uploads_dir: Optional[Path] = None,
    session_files: Optional[list] = None,
    session_images: Optional[list] = None,
    db_connection_tool: Optional[DatabaseConnectionTool] = None,
) -> Dict[str, object]:
    """
    Create default tool set for agents.
    
    Args:
        session_uploads_dir: Directory for file uploads
        session_files: List of session files metadata
        session_images: List of session images metadata
        db_connection_tool: Database connection tool instance
    
    Returns:
        Dictionary of tool name -> tool instance
    """
    tools = {
        "time_now": TimeTool(),
        "http_get": HttpGetTool(),
    }

    # File tools
    if session_uploads_dir:
        tools["file_read"] = FileReadTool(session_uploads_dir=session_uploads_dir)
    if session_files is not None:
        tools["file_list"] = FileListTool(session_files=session_files)

    # Image tools
    if session_uploads_dir:
        tools["image_analyze"] = ImageAnalysisTool(session_uploads_dir=session_uploads_dir)
    if session_images is not None:
        tools["image_list"] = ImageListTool(session_images=session_images)

    # Database tools
    if db_connection_tool:
        tools["db_schema"] = SchemaIntrospectionTool(connection_tool=db_connection_tool)
        tools["db_query"] = DatabaseQueryTool(connection_tool=db_connection_tool)

    return tools
