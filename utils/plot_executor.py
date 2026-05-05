"""Safe Python plot code executor using subprocess isolation."""

import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any


def execute_plot_code(python_code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python plotting code in a safe subprocess environment.
    
    Args:
        python_code: Python code string (matplotlib/seaborn/pandas plotting)
        timeout: Maximum execution time in seconds (default: 30)
    
    Returns:
        Dict with:
            - success: bool
            - image_base64: str (if success)
            - format: str (if success, e.g. "png")
            - error: str (if failure)
    """
    # Create a temporary directory for the output
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "plot_output.png"
        
        # Wrap the user code with matplotlib setup and savefig
        wrapper_code = f"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# User code
{python_code}

# Save the figure
try:
    fig = plt.gcf()
    if fig.get_axes():
        plt.savefig(r'{output_path}', bbox_inches='tight', dpi=150, format='png')
        plt.close('all')
    else:
        raise ValueError("No plot was created")
except Exception as e:
    # If user code already saved, that's ok
    import os
    if not os.path.exists(r'{output_path}'):
        raise
"""
        
        # Write the wrapped code to a temporary file
        code_path = Path(temp_dir) / "plot_code.py"
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(wrapper_code)
        
        # Prepare the subprocess environment
        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"
        
        try:
            # Execute the code in a subprocess
            result = subprocess.run(
                ["python", str(code_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=temp_dir
            )
            
            # Check if execution was successful
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return {
                    "success": False,
                    "error": f"Execution failed: {error_msg[:500]}"
                }
            
            # Check if the output file was created
            if not output_path.exists():
                return {
                    "success": False,
                    "error": "No plot output was generated. Make sure the code creates a plot using matplotlib, seaborn, or pandas."
                }
            
            # Read and encode the image
            with open(output_path, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            return {
                "success": True,
                "image_base64": image_base64,
                "format": "png"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }


def is_plotting_code(python_code: str) -> bool:
    """
    Check if Python code appears to be plotting/visualization code.
    
    Args:
        python_code: Python code string
    
    Returns:
        True if code contains plotting keywords
    """
    plotting_keywords = [
        "plt.",
        "sns.",
        ".plot(",
        "px.",
        "go.",
        "seaborn",
        "matplotlib",
        "plotly",
        "plt.figure",
        "plt.subplot",
        "plt.show",
        "sns.bar",
        "sns.line",
        "sns.hist",
    ]
    
    code_lower = python_code.lower()
    return any(keyword.lower() in code_lower for keyword in plotting_keywords)
