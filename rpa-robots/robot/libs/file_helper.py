"""File helper utilities for Robot Framework - file operations and path handling."""
import os
import sys
from pathlib import Path
from typing import List, Optional

# Import path configuration for centralized path handling
try:
    import path_config
except ImportError:
    # If direct import fails, add libs directory to path and try again
    libs_dir = Path(__file__).parent
    if str(libs_dir) not in sys.path:
        sys.path.insert(0, str(libs_dir))
    import path_config


def get_pdf_files_for_doc_transportes(doc_transportes: str, exclude_pod: bool = True) -> List[str]:
    """
    Get all PDF files for a doc_transportes from processado folder, excluding POD files.
    
    Args:
        doc_transportes: The doc_transportes ID (e.g., "96722724")
        exclude_pod: If True, exclude files containing "POD" in the name (case-insensitive)
    
    Returns:
        List of absolute file paths to PDF files
    """
    processado_dir = path_config.get_processado_dir()
    doc_folder = processado_dir / doc_transportes
    
    if not doc_folder.exists():
        return []
    
    pdf_files = []
    for file_path in doc_folder.glob("*.pdf"):
        filename = file_path.name
        # Exclude POD files if requested
        if exclude_pod and "POD" in filename.upper():
            continue
        pdf_files.append(str(file_path.absolute()))
    
    # Sort for consistent ordering
    pdf_files.sort()
    return pdf_files


def get_processado_folder_path(doc_transportes: str) -> str:
    """
    Get the absolute path to the processado folder for a doc_transportes.
    
    Args:
        doc_transportes: The doc_transportes ID (e.g., "96722724")
    
    Returns:
        Absolute path to the folder
    """
    processado_dir = path_config.get_processado_dir()
    doc_folder = processado_dir / doc_transportes
    return str(doc_folder.absolute())


def join_file_paths_for_upload(file_paths: List[str]) -> str:
    """
    Join multiple file paths into a single string for file input (Selenium uses newline separator).
    
    Args:
        file_paths: List of absolute file paths
    
    Returns:
        Newline-separated string of file paths
    """
    return "\n".join(file_paths)

