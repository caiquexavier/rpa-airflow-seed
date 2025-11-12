"""Service for posting execution results to callback URLs."""
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


def post_callback(
    callback_url: str,
    exec_id: int,
    rpa_key_id: str,
    status: str,
    rpa_response: Dict[str, Any],
    error_message: Optional[str] = None
) -> bool:
    """Post execution result to callback URL.
    
    Args:
        callback_url: The callback URL to post to
        exec_id: Execution ID
        rpa_key_id: RPA key identifier
        status: Execution status (SUCCESS or FAIL)
        rpa_response: RPA response payload
        error_message: Optional error message
        
    Returns:
        True if callback was successful, False otherwise
    """
    try:
        payload = {
            "exec_id": exec_id,
            "rpa_key_id": rpa_key_id,
            "status": status,
            "rpa_response": rpa_response,
            "error_message": error_message
        }
        
        response = requests.post(
            callback_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully posted callback for exec_id={exec_id} to {callback_url}")
            return True
        else:
            logger.warning(
                f"Callback POST failed for exec_id={exec_id} to {callback_url}: "
                f"status_code={response.status_code}, response={response.text}"
            )
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"Callback POST timeout for exec_id={exec_id} to {callback_url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Callback POST error for exec_id={exec_id} to {callback_url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error posting callback for exec_id={exec_id}: {e}")
        return False

