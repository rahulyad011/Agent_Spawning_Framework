from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from runtime_agents.shared.base import AgentResult
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

logger = get_logger(__name__)


@dataclass(frozen=True)
class AgentTemplate:
    """A versionable, pre-approved agent spec.

    In production, keep templates in source control (and ideally version them).
    """

    key: str
    name: str
    system_prompt: str
    tool_names: List[str]


@dataclass
class AgentInstance:
    """A runtime-spawned instance created from an AgentTemplate."""

    template: AgentTemplate
    llm: LLMClient
    tools: Dict[str, Tool]  # scoped toolset

    async def run(self, user_input: str, *, context: Optional[str] = None) -> AgentResult:
        logger.debug(f"[AGENT:{self.template.name}] Starting execution")
        logger.debug(f"[AGENT:{self.template.name}] User input: {user_input[:100]}...")
        logger.debug(f"[AGENT:{self.template.name}] Has context: {context is not None}")
        logger.debug(f"[AGENT:{self.template.name}] Available tools: {list(self.tools.keys())}")
        
        sys = self.template.system_prompt
        
        # Add session context (files, images, databases) if available
        if context:
            # Check if context contains session resource information (starts with "Available resources:")
            if context.startswith("Available resources:"):
                logger.debug(f"[AGENT:{self.template.name}] Adding session resource context")
                sys += "\n\n" + context
            else:
                # It's agent context from previous agents
                logger.debug(f"[AGENT:{self.template.name}] Adding agent context from previous agents")
            sys += "\n\nContext (from other agents):\n" + context

        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        sys += "\n\nAvailable tools:\n" + (tool_catalog if tool_catalog else "- (none)")
        
        # Add instructions about using tools
        if any(t.name in ["file_read", "db_query", "image_analyze"] for t in self.tools.values()):
            sys += "\n\nIMPORTANT: When the user asks about uploaded files, images, or database data, you should reference the specific files/tables available and explain how you would access them using the tools. For example: 'I can read the file X using the file_read tool' or 'I can query the database using db_query to get the data you need'."

        messages = [
            Message(role="system", content=sys),
            Message(role="user", content=user_input),
        ]

        logger.debug(f"[AGENT:{self.template.name}] Calling LLM with {len(messages)} messages")
        text = await self.llm.chat(messages, temperature=0.2)
        logger.debug(f"[AGENT:{self.template.name}] LLM response received (length: {len(text)} chars)")

        # Auto-execute tools if user or agent mentions files/databases
        tool_calls = []
        tool_results = []
        
        # Check if user input or agent response mentions files and we have file_read tool
        # Check both user input and agent response for file references
        # Also check user input directly for file analysis requests
        user_input_lower = user_input.lower()
        combined_text = (user_input + " " + text).lower()
        referenced_files = self._extract_file_references(combined_text, context)
        
        # If user asks to analyze/read/examine a file, automatically include it
        analysis_keywords = ["analyze", "read", "examine", "look at", "check", "review", "process"]
        if "file_read" in self.tools and any(keyword in user_input_lower for keyword in analysis_keywords):
            # Get all available files and check if user mentions any
            available_files = self._get_available_files(context)
            for filename in available_files:
                filename_base = filename.split('.')[0].lower()
                # If user mentions the file base name or asks about "the file" or "dataset"
                if (filename_base in user_input_lower or 
                    ("file" in user_input_lower and len(available_files) == 1) or
                    ("dataset" in user_input_lower and ".csv" in filename)):
                    if filename not in referenced_files:
                        referenced_files.append(filename)
                        logger.info(f"[AGENT:{self.template.name}] Auto-detected file from user request: {filename}")
        
        if "file_read" in self.tools and referenced_files:
            logger.info(f"[AGENT:{self.template.name}] Detected file references: {referenced_files}, executing file_read tool")
            for filename in referenced_files:
                try:
                    logger.debug(f"[AGENT:{self.template.name}] Reading file: {filename}")
                    result = await self.tools["file_read"]({"filename": filename})
                    tool_calls.append({"tool": "file_read", "input": {"filename": filename}, "result": result})
                    
                    # Extract content based on file type
                    content = result.get('content', '')
                    if result.get('type') == 'csv':
                        content = result.get('content', '')[:2000]  # CSV can be large
                    else:
                        content = content[:2000]  # Limit content size
                    
                    tool_results.append(f"File '{filename}' content:\n{content}")
                    logger.debug(f"[AGENT:{self.template.name}] File read successful: {filename} ({len(content)} chars)")
                except Exception as e:
                    logger.warning(f"[AGENT:{self.template.name}] Error reading file {filename}: {e}")
                    tool_calls.append({"tool": "file_read", "input": {"filename": filename}, "result": {"error": str(e)}})
                    tool_results.append(f"Error reading file '{filename}': {str(e)}")
        
        # If we got tool results, get agent to process them
        if tool_results:
            logger.info(f"[AGENT:{self.template.name}] Got {len(tool_results)} tool results, requesting agent to process")
            follow_up_messages = messages + [
                Message(role="assistant", content=text),
                Message(role="user", content=f"Here is the data from the tools I executed:\n\n" + "\n\n".join(tool_results) + "\n\nPlease analyze this data and provide your comprehensive answer based on the actual file contents."),
            ]
            text = await self.llm.chat(follow_up_messages, temperature=0.2)
            logger.debug(f"[AGENT:{self.template.name}] Final response after tool execution (length: {len(text)} chars)")

        return AgentResult(agent_name=self.template.name, output=text, tool_calls=tool_calls)
    
    def _get_available_files(self, context: Optional[str] = None) -> List[str]:
        """Get list of available files from context."""
        available_files = []
        if context and "Uploaded files available:" in context:
            # Extract file names from context - match pattern like "- filename.csv (type, size)"
            file_pattern = r"-\s+([^\s(]+\.(?:csv|txt|json|pdf|md|py|log|docx|xlsx))"
            available_files = re.findall(file_pattern, context)
        return available_files
    
    def _extract_file_references(self, text: str, context: Optional[str] = None) -> List[str]:
        """Extract file references from agent output and context."""
        files = []
        
        # Get available files from context
        available_files = self._get_available_files(context)
        logger.debug(f"[AGENT:{self.template.name}] Found {len(available_files)} available files in context: {available_files}")
        
        # Check if text mentions any of the available files
        text_lower = text.lower()
        for filename in available_files:
            filename_lower = filename.lower()
            filename_base = filename.split('.')[0].lower()
            
            # Check for exact filename match or base name match
            if filename_lower in text_lower or filename_base in text_lower:
                # Also check for common patterns like "the file X", "X file", "analyze X"
                patterns = [
                    rf"\b{re.escape(filename_lower)}\b",
                    rf"\b{re.escape(filename_base)}\b.*file",
                    rf"file.*\b{re.escape(filename_base)}\b",
                    rf"analyze.*\b{re.escape(filename_base)}\b",
                    rf"\b{re.escape(filename_base)}\b.*dataset",
                ]
                
                if any(re.search(pattern, text_lower) for pattern in patterns):
                    if filename not in files:
                        files.append(filename)
                        logger.debug(f"[AGENT:{self.template.name}] Matched file reference: {filename}")
        
        return files
