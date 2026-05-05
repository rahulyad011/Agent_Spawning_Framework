"""Visualization tools for agents to render plots and diagrams."""

from dataclasses import dataclass
from typing import Any, Dict

from utils.plot_executor import execute_plot_code


@dataclass
class RenderPlotTool:
    """Tool for rendering matplotlib/seaborn plots from Python code."""
    
    name: str = "render_plot"
    description: str = (
        "Render a matplotlib/seaborn/pandas plot from Python code. "
        "Input: {python_code: string}. "
        "The code should create a plot using matplotlib (plt), seaborn (sns), or pandas plotting methods. "
        "Returns a rendered image of the plot."
    )
    
    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plotting code and return rendered image.
        
        Args:
            input: Dict with 'python_code' key
        
        Returns:
            Dict with 'type', 'image_base64', 'format', and optional 'error'
        """
        python_code = input.get("python_code")
        
        if not python_code:
            return {
                "type": "plot",
                "error": "Missing 'python_code' in input"
            }
        
        # Execute the code using the shared executor
        result = execute_plot_code(python_code)
        
        if result["success"]:
            return {
                "type": "plot",
                "image_base64": result["image_base64"],
                "format": result["format"],
                "error": None
            }
        else:
            return {
                "type": "plot",
                "error": result["error"]
            }


@dataclass
class RenderMermaidTool:
    """Tool for validating and preparing Mermaid diagrams for rendering."""
    
    name: str = "render_mermaid"
    description: str = (
        "Display a Mermaid diagram. "
        "Input: {mermaid_code: string}. "
        "The code should be valid Mermaid syntax (graph, flowchart, sequenceDiagram, classDiagram, etc.). "
        "Returns the validated Mermaid code ready for rendering."
    )
    
    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and prepare Mermaid code for rendering.
        
        Args:
            input: Dict with 'mermaid_code' key
        
        Returns:
            Dict with 'type', 'code', and optional 'error'
        """
        mermaid_code = input.get("mermaid_code")
        
        if not mermaid_code:
            return {
                "type": "mermaid",
                "error": "Missing 'mermaid_code' in input"
            }
        
        # Validate that it looks like Mermaid syntax
        code_lower = mermaid_code.strip().lower()
        
        valid_diagram_types = [
            "graph ",
            "flowchart ",
            "sequencediagram",
            "classdiagram",
            "erdiagram",
            "gantt",
            "pie",
            "statediagram",
            "journey",
            "gitgraph",
            "c4context",
            "mindmap",
            "timeline",
            "quadrantchart",
            "requirementdiagram"
        ]
        
        is_valid = any(code_lower.startswith(dtype) for dtype in valid_diagram_types)
        
        if not is_valid:
            return {
                "type": "mermaid",
                "error": (
                    f"Invalid Mermaid syntax. Diagram must start with a valid type: "
                    f"graph, flowchart, sequenceDiagram, classDiagram, etc. "
                    f"Got: {mermaid_code[:50]}..."
                )
            }
        
        return {
            "type": "mermaid",
            "code": mermaid_code.strip(),
            "error": None
        }
