from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image


@dataclass
class ImageAnalysisTool:
    """Analyze images using vision models."""

    name: str = "image_analyze"
    description: str = "Analyze an image. Input: {filename: string}."

    session_uploads_dir: Optional[Path] = None
    llm_client: Optional[Any] = None  # Will be set to OpenAIChatClient

    def _encode_image(self, image_path: Path) -> Optional[str]:
        """Encode image to base64."""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        filename = input.get("filename")
        if not filename:
            return {"error": "Missing 'filename'."}

        if not self.session_uploads_dir:
            return {"error": "Session uploads directory not set."}

        image_path = self.session_uploads_dir / "images" / filename
        if not image_path.exists():
            return {"error": f"Image '{filename}' not found."}

        try:
            # Get image metadata
            with Image.open(image_path) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode

            # Encode image for API
            base64_image = self._encode_image(image_path)
            if not base64_image:
                return {"error": "Failed to encode image."}

            # If LLM client supports vision, use it
            if self.llm_client and hasattr(self.llm_client, "chat_with_vision"):
                try:
                    analysis = await self.llm_client.chat_with_vision(
                        base64_image, image_path.suffix
                    )
                    return {
                        "filename": filename,
                        "analysis": analysis,
                        "metadata": {
                            "width": width,
                            "height": height,
                            "format": format_name,
                            "mode": mode,
                        },
                    }
                except Exception as e:
                    return {
                        "error": f"Vision analysis failed: {str(e)}",
                        "metadata": {
                            "width": width,
                            "height": height,
                            "format": format_name,
                            "mode": mode,
                        },
                    }

            # Fallback: return metadata only
            return {
                "filename": filename,
                "metadata": {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                },
                "note": "Vision analysis not available. LLM client does not support vision.",
            }

        except Exception as e:
            return {"error": f"Error processing image: {str(e)}"}


@dataclass
class ImageListTool:
    """List images uploaded in the current session."""

    name: str = "image_list"
    description: str = "List all images uploaded in the current session."

    session_images: Optional[List[Dict[str, Any]]] = None

    async def __call__(self, input: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_images:
            return {"images": []}

        image_list = [
            {
                "filename": img.get("filename", "unknown"),
                "image_format": img.get("image_format", "unknown"),
                "size_bytes": img.get("size_bytes", 0),
            }
            for img in self.session_images
        ]

        return {"images": image_list, "count": len(image_list)}
