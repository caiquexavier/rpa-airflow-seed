"""Error extraction utilities for Robot Framework output."""
import re
from typing import Optional


RETRY_LOOP_PATTERNS = [
    r'\[ WARN \].*Retrying.*after connection broken',
    r'\[ WARN \].*Retrying.*Retry\(total=',
    r'Retrying.*after connection broken by.*NewConnectionError',
    r'NewConnectionError.*Failed to establish.*\[WinError',
    r'Connection.*refused.*retrying',
    r'Failed to establish.*Nenhuma liga',
]

RETRY_PATTERNS_IN_OUTPUT = [
    r'\[ WARN \].*Retrying.*after connection broken.*NewConnectionError',
    r'Retrying.*after connection broken by.*NewConnectionError.*Failed to establish',
    r'NewConnectionError.*Failed to establish.*\[WinError \d+\]',
]

CONNECTION_ERROR_PATTERNS = [
    r'HTTPConnectionPool.*Max retries exceeded',
    r'Failed to establish a new connection',
    r'Connection refused',
    r'ConnectionError',
    r'NewConnectionError',
]

WARN_ERROR_PATTERNS = [
    r'\[ WARN \].*could not be run on failure:.*',
    r'\[ WARN \].*Retrying.*',
    r'\[ ERROR \].*',
    r'FAIL:.*',
]

EXCEPTION_PATTERNS = [
    r'Exception:\s*(.+?)(?:\n|$)',
    r'Error:\s*(.+?)(?:\n|$)',
    r'Traceback.*?\n\s*(\w+Error[^\n]*)',
]


def is_retry_loop_line(line: str) -> bool:
    """Check if line indicates a retry loop pattern."""
    for pattern in RETRY_LOOP_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def extract_retry_error_from_line(line: str) -> str:
    """Extract meaningful error from retry line."""
    if 'NewConnectionError' in line:
        # Try to extract WinError details
        match = re.search(r'\[WinError\s+(\d+)\]([^\']*)', line, re.IGNORECASE | re.DOTALL)
        if match:
            error_code = match.group(1)
            error_msg = match.group(2).strip()[:150]
            return f"Connection failed: WinError {error_code} - {error_msg}"
        
        # Try to extract "Failed to establish" message
        match = re.search(r"Failed to establish[^']*(\[WinError[^\]]+\][^']*)", line, re.IGNORECASE | re.DOTALL)
        if match:
            error_detail = match.group(1).strip()[:200]
            return f"Connection failed: {error_detail}"
        
        # Fallback: extract session path
        match = re.search(r":\s*(/session/[^'\s]+)", line)
        if match:
            return f"Connection failed to {match.group(1)}"
    
    # If it's a retry line but no NewConnectionError
    if 'Retrying' in line and 'connection broken' in line:
        match = re.search(r":\s*(/session/[^'\s]+)", line)
        if match:
            return f"Retry loop: Connection broken to {match.group(1)}"
    
    # Default: return first 300 chars
    return line.strip()[:300]


def extract_error_from_output_text(output_text: str) -> Optional[str]:
    """Extract error messages from robot output text."""
    if not output_text:
        return None
    
    # Check for retry loop patterns first (highest priority)
    for pattern in RETRY_PATTERNS_IN_OUTPUT:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            lines = output_text.split('\n')
            for line in lines:
                if re.search(pattern, line, re.IGNORECASE | re.DOTALL):
                    return extract_retry_error_from_line(line)
    
    # Check for HTTPConnectionPool errors
    for pattern in CONNECTION_ERROR_PATTERNS:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE)
        if match:
            lines = output_text.split('\n')
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    context = line.strip()
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        context += f": {lines[i + 1].strip()[:200]}"
                    return context[:300]
    
    # Check for WARN/ERROR keywords
    for pattern in WARN_ERROR_PATTERNS:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE)
        if match:
            error_line = match.group(0).strip()
            return error_line[:300]
    
    # Check for common exception patterns
    for pattern in EXCEPTION_PATTERNS:
        match = re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            error_msg = match.group(1) if match.lastindex >= 1 else match.group(0)
            return error_msg.strip()[:300]
    
    return None

