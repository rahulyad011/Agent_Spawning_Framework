"""Response parser for extracting structured content from agent responses."""

import re
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field


class ParsedResponse(BaseModel):
    """Structured representation of parsed agent response."""
    
    text_parts: List[str] = Field(default_factory=list, description="Normal prose text sections")
    python_blocks: List[str] = Field(default_factory=list, description="Python code blocks")
    mermaid_blocks: List[str] = Field(default_factory=list, description="Mermaid diagram blocks")
    sql_blocks: List[str] = Field(default_factory=list, description="SQL code blocks")
    other_code_blocks: List[Tuple[str, str]] = Field(default_factory=list, description="Other code blocks (language, code)")


def parse_response(content: str, try_json: bool = False) -> ParsedResponse:
    """
    Parse agent response into structured components.
    
    Args:
        content: Raw response text from agent
        try_json: If True, attempt JSON parsing first (optional structured output)
    
    Returns:
        ParsedResponse with categorized content
    """
    if try_json:
        # Try LangChain PydanticOutputParser for structured JSON output
        try:
            parsed = _parse_json_response(content)
            if parsed:
                return parsed
        except Exception:
            # Fall through to markdown parsing
            pass
    
    # Default: Parse markdown code blocks
    return _parse_markdown_response(content)


def _parse_json_response(content: str) -> Optional[ParsedResponse]:
    """
    Parse JSON-formatted response using LangChain (optional path).
    
    Args:
        content: Response content that may be JSON
    
    Returns:
        ParsedResponse if successful, None otherwise
    """
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        
        # Try to parse as JSON - simplified approach
        # In production, you'd define a specific schema and use parser.get_format_instructions()
        import json
        
        # Strip markdown code fences if present
        stripped = content.strip()
        if stripped.startswith("```json"):
            stripped = stripped[7:]
        if stripped.startswith("```"):
            stripped = stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()
        
        # Try to parse as JSON
        if stripped.startswith("{"):
            data = json.loads(stripped)
            
            # Extract fields based on common patterns
            text = data.get("text", data.get("summary", data.get("content", "")))
            python_blocks = data.get("python_code", data.get("python_blocks", []))
            mermaid_blocks = data.get("mermaid_code", data.get("mermaid_blocks", []))
            sql_blocks = data.get("sql_code", data.get("sql_blocks", []))
            
            # Handle visualizations list if present
            if "visualizations" in data:
                for viz in data["visualizations"]:
                    if viz.get("type") == "plot" and "code" in viz:
                        python_blocks.append(viz["code"])
                    elif viz.get("type") == "mermaid" and "code" in viz:
                        mermaid_blocks.append(viz["code"])
            
            # Ensure lists
            if isinstance(python_blocks, str):
                python_blocks = [python_blocks]
            if isinstance(mermaid_blocks, str):
                mermaid_blocks = [mermaid_blocks]
            if isinstance(sql_blocks, str):
                sql_blocks = [sql_blocks]
            
            return ParsedResponse(
                text_parts=[text] if text else [],
                python_blocks=python_blocks,
                mermaid_blocks=mermaid_blocks,
                sql_blocks=sql_blocks,
                other_code_blocks=[]
            )
    except Exception:
        pass
    
    return None


def _parse_markdown_response(content: str) -> ParsedResponse:
    """
    Parse markdown-formatted response with code blocks.
    
    Args:
        content: Response content with markdown code blocks
    
    Returns:
        ParsedResponse with extracted content
    """
    # Pattern to match fenced code blocks: ```language\n...\n```
    code_block_pattern = r"```(\w*)\n(.*?)```"
    
    text_parts = []
    python_blocks = []
    mermaid_blocks = []
    sql_blocks = []
    other_code_blocks = []
    
    # Find all code blocks
    matches = list(re.finditer(code_block_pattern, content, re.DOTALL))
    
    if not matches:
        # No code blocks found, return all as text
        return ParsedResponse(
            text_parts=[content.strip()] if content.strip() else [],
            python_blocks=[],
            mermaid_blocks=[],
            sql_blocks=[],
            other_code_blocks=[]
        )
    
    # Extract text and code blocks in order
    last_end = 0
    
    for match in matches:
        # Get text before this code block
        text_before = content[last_end:match.start()].strip()
        if text_before:
            text_parts.append(text_before)
        
        # Get language and code
        language = match.group(1).lower() if match.group(1) else ""
        code = match.group(2).strip()
        
        # Categorize by language
        if language in ("python", "py"):
            python_blocks.append(code)
        elif language == "mermaid":
            mermaid_blocks.append(code)
        elif language in ("sql", "postgres", "postgresql", "mysql", "sqlite"):
            sql_blocks.append(code)
        elif language:
            other_code_blocks.append((language, code))
        else:
            # No language specified, try to guess or treat as text
            if _looks_like_python(code):
                python_blocks.append(code)
            elif _looks_like_mermaid(code):
                mermaid_blocks.append(code)
            elif _looks_like_sql(code):
                sql_blocks.append(code)
            else:
                # Unknown, keep as other
                other_code_blocks.append(("unknown", code))
        
        last_end = match.end()
    
    # Get any remaining text after the last code block
    text_after = content[last_end:].strip()
    if text_after:
        text_parts.append(text_after)
    
    return ParsedResponse(
        text_parts=text_parts,
        python_blocks=python_blocks,
        mermaid_blocks=mermaid_blocks,
        sql_blocks=sql_blocks,
        other_code_blocks=other_code_blocks
    )


def _looks_like_python(code: str) -> bool:
    """Heuristic to detect if code looks like Python."""
    python_keywords = ["import ", "def ", "class ", "print(", "plt.", "sns.", "pandas", "numpy"]
    code_lower = code.lower()
    return any(keyword in code_lower for keyword in python_keywords)


def _looks_like_mermaid(code: str) -> bool:
    """Heuristic to detect if code looks like Mermaid diagram."""
    mermaid_keywords = ["graph ", "flowchart ", "sequenceDiagram", "classDiagram", "erDiagram", "gantt", "pie"]
    code_lower = code.lower()
    return any(keyword.lower() in code_lower for keyword in mermaid_keywords)


def _looks_like_sql(code: str) -> bool:
    """Heuristic to detect if code looks like SQL."""
    sql_keywords = ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "DROP ", "FROM ", "WHERE "]
    code_upper = code.upper()
    return any(keyword in code_upper for keyword in sql_keywords)
