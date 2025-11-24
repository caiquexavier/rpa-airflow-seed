"""
Path configuration for RPA robots.

This module provides centralized path handling for the rpa-airflow-seed project.
It automatically detects the project root by searching for 'rpa-airflow-seed' in the path,
ensuring consistent path resolution regardless of where the code is executed from.
"""
import os
from pathlib import Path
from typing import Optional

# Project root identifier - change this if the project is renamed
PROJECT_ROOT_NAME = "rpa-airflow-seed"

# Cached project root path (computed once on first access)
_project_root: Optional[Path] = None


def find_project_root(start_path: Optional[str] = None) -> Path:
    """
    Find the project root directory by searching for PROJECT_ROOT_NAME in the path.
    
    Searches upward from the start_path (or current working directory) until it finds
    a directory named PROJECT_ROOT_NAME.
    
    Args:
        start_path: Starting path for the search. If None, uses os.getcwd().
        
    Returns:
        Path to the project root directory.
        
    Raises:
        FileNotFoundError: If the project root cannot be found.
    """
    if start_path is None:
        start_path = os.getcwd()
    
    current = Path(start_path).resolve()
    
    # Search upward until we find the project root
    for path in [current] + list(current.parents):
        if path.name == PROJECT_ROOT_NAME:
            return path
    
    # If not found, try searching from common locations
    common_paths = [
        Path(__file__).resolve(),  # Start from this file's location
        Path(os.getcwd()).resolve(),
    ]
    
    for start in common_paths:
        for path in [start] + list(start.parents):
            if path.name == PROJECT_ROOT_NAME:
                return path
    
    raise FileNotFoundError(
        f"Project root '{PROJECT_ROOT_NAME}' not found. "
        f"Searched from: {start_path}"
    )


def get_project_root() -> Path:
    """
    Get the project root directory path (cached).
    
    Returns:
        Path to the project root directory.
    """
    global _project_root
    if _project_root is None:
        _project_root = find_project_root()
    return _project_root


def get_shared_downloads_dir() -> Path:
    """
    Get the shared/downloads directory path.
    
    Returns:
        Path to the shared/downloads directory.
    """
    return get_project_root() / "shared" / "downloads"


def get_shared_data_dir() -> Path:
    """
    Get the shared/data directory path.
    
    Returns:
        Path to the shared/data directory.
    """
    return get_project_root() / "shared" / "data"


def get_path_as_string(path: Path) -> str:
    """
    Convert a Path object to a string, normalized for the current OS.
    
    Args:
        path: Path object to convert.
        
    Returns:
        String representation of the path.
    """
    return str(path.resolve())


# Convenience functions that return strings (for Robot Framework compatibility)
def get_downloads_dir() -> str:
    """
    Get the shared/downloads directory path as a string.
    
    Returns:
        Absolute path to the shared/downloads directory as a string.
    """
    return get_path_as_string(get_shared_downloads_dir())


def get_data_dir() -> str:
    """
    Get the shared/data directory path as a string.
    
    Returns:
        Absolute path to the shared/data directory as a string.
    """
    return get_path_as_string(get_shared_data_dir())


def list_pdf_files(download_dir: Optional[str] = None) -> set:
    """
    List all PDF files in the download directory.
    
    Args:
        download_dir: Path to the download directory. If None, uses get_downloads_dir().
        
    Returns:
        Set of PDF filenames.
    """
    if download_dir is None:
        download_dir = get_downloads_dir()
    normalized_dir = os.path.normpath(download_dir)
    return set([f for f in os.listdir(normalized_dir) if f.endswith('.pdf')])


def get_latest_file(download_dir: Optional[str] = None, new_files: Optional[list] = None) -> str:
    """
    Get the latest file from a list of new files in the download directory.
    
    Args:
        download_dir: Path to the download directory. If None, uses get_downloads_dir().
        new_files: List of new filenames.
        
    Returns:
        Path to the latest file.
    """
    if download_dir is None:
        download_dir = get_downloads_dir()
    if new_files is None:
        raise ValueError("new_files is required")
    normalized_dir = os.path.normpath(download_dir)
    file_paths = [os.path.join(normalized_dir, f) for f in new_files]
    return max(file_paths, key=lambda p: os.path.getmtime(p))


def get_file_size(file_path) -> int:
    """
    Get the size of a file.
    Accepts either a string path or a Path object.
    
    Args:
        file_path: Path to the file (str or Path object).
        
    Returns:
        File size in bytes.
    """
    # Convert to Path object if it's a string, which handles Windows paths correctly
    if isinstance(file_path, str):
        file_path = Path(file_path)
    elif not isinstance(file_path, Path):
        file_path = Path(str(file_path))
    
    return file_path.stat().st_size


def get_file_size_from_path_str(file_path_str: str) -> int:
    """
    Get the size of a file from a path string.
    This function safely handles paths that may have been converted from backslashes to forward slashes.
    
    Args:
        file_path_str: Path to the file as a string (with forward slashes).
        
    Returns:
        File size in bytes.
    """
    # Path handles both forward and backward slashes correctly on all platforms
    return Path(file_path_str).stat().st_size

