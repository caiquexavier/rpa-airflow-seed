"""GPT PDF rotation service - Detect PDF rotation using GPT Vision."""
import logging
import base64
import io
from typing import Dict, Any

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ...infrastructure.llm.pdf_extractor import detect_rotation_with_vision

logger = logging.getLogger(__name__)


def detect_pdf_rotation(page_image_base64: str) -> Dict[str, Any]:
    """
    Detect PDF page rotation/orientation using GPT Vision API.
    Prefers landscape orientation (90° or 270°).
    
    Args:
        page_image_base64: Base64-encoded image of the PDF page
        
    Returns:
        Dictionary with 'rotation' (0, 90, 180, or 270), 'confidence' (0-100), and 'reasoning'
        
    Raises:
        RuntimeError: If PIL is not available or GPT Vision API call fails
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow not available. Install Pillow to process images.")
    
    try:
        result = detect_rotation_with_vision(page_image_base64)
        
        rotation = result.get("rotation", 0)
        confidence = result.get("confidence", 0)
        reasoning = result.get("reasoning", "")
        
        logger.info(
            "GPT Vision rotation detection: %s° (confidence: %.1f%%, reasoning: %s)",
            rotation, confidence, reasoning[:100] if reasoning else "N/A"
        )
        
        return {
            "rotation": rotation,
            "confidence": confidence,
            "reasoning": reasoning
        }
    except Exception as e:
        logger.error("GPT Vision rotation detection failed: %s", e)
        raise RuntimeError(f"Failed to detect rotation with GPT Vision: {e}") from e

