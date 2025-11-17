"""Application layer - orchestrates domain logic for message processing."""
from pathlib import Path
from typing import Dict

from ..domain.message.handler import handle_message


def process_message(
    message: Dict,
    project_path: Path,
    robot_exe: Path,
    tests_path: Path,
    results_dir: Path
) -> bool:
    """
    Process a message by orchestrating domain logic.
    
    This is the application layer entry point that coordinates
    message handling across domains (robot, saga, message).
    
    Args:
        message: The message dictionary from RabbitMQ
        project_path: Path to robot project directory
        robot_exe: Path to robot executable
        tests_path: Path to robot test files
        results_dir: Path to results directory
        
    Returns:
        True if processing succeeded, False otherwise
    """
    return handle_message(
        message,
        project_path,
        robot_exe,
        tests_path,
        results_dir
    )

