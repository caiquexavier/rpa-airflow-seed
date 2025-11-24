"""Parsing utilities for JSON, strings, and data transformation."""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_json_string(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON string to dictionary.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    if not json_string or not json_string.strip():
        return None
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON string: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error parsing JSON: {e}")
        return None


def extract_json_path(data: Dict[str, Any], json_path: str) -> Optional[Any]:
    """
    Extract value from dictionary using JSON path notation.
    
    Args:
        data: Dictionary to extract from
        json_path: JSON path (e.g., "$.data.doc_transportes_list[*]")
        
    Returns:
        Extracted value or None if not found
    """
    # Simple implementation for common paths
    # For full JSONPath support, consider using jsonpath-ng library
    if not json_path or not json_path.startswith("$."):
        return None
    
    path_parts = json_path[2:].split(".")
    current = data
    
    try:
        for part in path_parts:
            if part.endswith("[*]"):
                key = part[:-3]
                if key in current:
                    return current[key] if isinstance(current[key], list) else [current[key]]
                return None
            elif "[" in part and "]" in part:
                # Handle array access like "list[0]"
                key = part.split("[")[0]
                index_str = part.split("[")[1].split("]")[0]
                if key in current:
                    current = current[key]
                    if isinstance(current, list) and index_str.isdigit():
                        index = int(index_str)
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            return None
                    else:
                        return None
                else:
                    return None
            else:
                if part in current:
                    current = current[part]
                else:
                    return None
        
        return current
    except (KeyError, TypeError, IndexError) as e:
        logger.debug(f"Failed to extract JSON path {json_path}: {e}")
        return None


def flatten_dict(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary.
    
    Args:
        data: Dictionary to flatten
        separator: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    def _flatten(obj: Any, parent_key: str = "", sep: str = separator) -> Dict[str, Any]:
        items: List[tuple] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.extend(_flatten(v, new_key, sep).items())
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
                items.extend(_flatten(v, new_key, sep).items())
        else:
            return {parent_key: obj} if parent_key else {}
        return dict(items)
    
    return _flatten(data)


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value.
    
    Args:
        data: Dictionary to get from
        keys: Keys to traverse
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

