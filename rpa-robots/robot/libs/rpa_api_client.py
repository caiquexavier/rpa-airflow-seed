"""RPA API client - generic HTTP client for rpa-api interactions."""
import os
import logging
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


def _get_api_base_url() -> str:
    """Get RPA API base URL from environment variable."""
    api_url = os.getenv("RPA_API_BASE_URL", "http://localhost:3000")
    if not api_url.endswith('/'):
        api_url = api_url.rstrip('/')
    return api_url


def call_api(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Make a generic API call to rpa-api.
    
    Args:
        endpoint: API endpoint (e.g., "/api/v1/saga/123")
        method: HTTP method (GET, POST, PUT, DELETE)
        payload: Optional request payload
        timeout: Request timeout in seconds
        
    Returns:
        Response JSON as dict if successful, None otherwise
    """
    base_url = _get_api_base_url()
    url = f"{base_url}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
        elif method.upper() == "PUT":
            response = requests.put(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=timeout)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return None
        
        if response.status_code in [200, 201]:
            try:
                return response.json()
            except ValueError:
                return {"status": "success", "status_code": response.status_code}
        else:
            logger.error(
                f"API call failed: {url} (status_code={response.status_code}, response={response.text})"
            )
            return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"API connection error to {url}: {e}")
        return None
    except Exception as e:
        logger.exception(f"API call exception to {url}: {type(e).__name__}: {e}")
        return None

