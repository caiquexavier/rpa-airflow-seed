"""Robot Framework parser service - Extracts test steps from Robot Framework files."""
import logging
import os
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RobotStep:
    """Represents a Robot Framework test step/keyword."""
    step_name: str
    step_type: str  # keyword, test_case, setup, teardown
    line_number: Optional[int] = None
    arguments: List[str] = None
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


@dataclass
class RobotTestStructure:
    """Represents Robot Framework test structure."""
    test_file: str
    test_cases: List[RobotStep]  # Test case definitions
    keywords: List[RobotStep]  # Keyword definitions and steps
    setup_steps: List[RobotStep] = None
    teardown_steps: List[RobotStep] = None
    
    def __post_init__(self):
        if self.setup_steps is None:
            self.setup_steps = []
        if self.teardown_steps is None:
            self.teardown_steps = []


def parse_robot_file(
    file_path: str,
    read_file_fn: Optional[Callable[[str], str]] = None
) -> RobotTestStructure:
    """
    Parse Robot Framework test file to extract test structure.
    
    Args:
        file_path: Path to .robot file
        read_file_fn: Optional function to read file (for testing)
        
    Returns:
        RobotTestStructure with parsed steps
    """
    if read_file_fn is None:
        read_file_fn = _default_read_file
    
    if not os.path.exists(file_path):
        logger.warning(f"Robot Framework file not found: {file_path}")
        return RobotTestStructure(
            test_file=file_path,
            test_cases=[],
            keywords=[]
        )
    
    content = read_file_fn(file_path)
    return parse_robot_content(content, file_path)


def _default_read_file(file_path: str) -> str:
    """Default file reader - reads file from filesystem."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_robot_content(content: str, file_path: str = "") -> RobotTestStructure:
    """
    Parse Robot Framework content to extract test structure - pure function.
    
    Args:
        content: Robot Framework file content
        file_path: Optional file path for reference
        
    Returns:
        RobotTestStructure with parsed steps
    """
    lines = content.split('\n')
    parser_state = _ParserState()
    
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        
        if not stripped or stripped.startswith('#'):
            continue  # Skip comments and empty lines
        
        if _is_section_header(stripped):
            parser_state.current_section = _extract_section_name(stripped)
            continue
        
        _process_line(line, stripped, line_number, parser_state)
    
    return RobotTestStructure(
        test_file=file_path,
        test_cases=parser_state.test_cases,
        keywords=parser_state.keywords,
        setup_steps=parser_state.setup_steps,
        teardown_steps=parser_state.teardown_steps
    )


class _ParserState:
    """Internal parser state for Robot Framework parsing."""
    
    def __init__(self):
        self.current_section: Optional[str] = None
        self.current_test_case: Optional[str] = None
        self.test_cases: List[RobotStep] = []
        self.keywords: List[RobotStep] = []
        self.setup_steps: List[RobotStep] = []
        self.teardown_steps: List[RobotStep] = []


def _is_section_header(line: str) -> bool:
    """Check if line is a section header - pure function."""
    return line.startswith('***') and line.endswith('***')


def _extract_section_name(line: str) -> Optional[str]:
    """Extract section name from header - pure function."""
    section_name = line.replace('*', '').strip().lower()
    if section_name in ('test cases', 'keywords', 'settings'):
        return section_name
    return None


def _process_line(
    line: str,
    stripped: str,
    line_number: int,
    state: _ParserState
) -> None:
    """Process a single line based on current section - pure function."""
    if state.current_section == 'test cases':
        _process_test_case_line(line, stripped, line_number, state)
    elif state.current_section == 'keywords':
        _process_keyword_line(line, stripped, line_number, state)
    elif state.current_section == 'settings':
        _process_settings_line(stripped, line_number, state)


def _process_test_case_line(
    line: str,
    stripped: str,
    line_number: int,
    state: _ParserState
) -> None:
    """Process line in test cases section - pure function."""
    if not line.startswith(' ') and not line.startswith('\t'):
        # Test case name (no indentation)
        state.current_test_case = stripped
        state.test_cases.append(RobotStep(
            step_name=stripped,
            step_type="test_case",
            line_number=line_number
        ))
    elif state.current_test_case and (line.startswith(' ') or line.startswith('\t')):
        # Keyword within test case (indented)
        keyword_match = re.match(r'^\s+(\w+(?:\s+\w+)*)', stripped)
        if keyword_match:
            keyword_name = keyword_match.group(1).strip()
            state.keywords.append(RobotStep(
                step_name=keyword_name,
                step_type="keyword",
                line_number=line_number
            ))


def _process_keyword_line(
    line: str,
    stripped: str,
    line_number: int,
    state: _ParserState
) -> None:
    """Process line in keywords section - pure function."""
    if not line.startswith(' ') and not line.startswith('\t'):
        # Keyword definition (no indentation)
        state.keywords.append(RobotStep(
            step_name=stripped,
            step_type="keyword",
            line_number=line_number
        ))


def _process_settings_line(
    stripped: str,
    line_number: int,
    state: _ParserState
) -> None:
    """Process line in settings section - pure function."""
    if stripped.lower().startswith('suite setup'):
        setup_name = stripped.replace('Suite Setup', '').strip()
        if setup_name:
            state.setup_steps.append(RobotStep(
                step_name=setup_name,
                step_type="setup",
                line_number=line_number
            ))
    elif stripped.lower().startswith('suite teardown'):
        teardown_name = stripped.replace('Suite Teardown', '').strip()
        if teardown_name:
            state.teardown_steps.append(RobotStep(
                step_name=teardown_name,
                step_type="teardown",
                line_number=line_number
            ))


def find_robot_file(
    rpa_key_id: str,
    robots_base_path: str = "rpa-robots",
    path_exists_fn: Optional[Callable[[str], bool]] = None,
    list_dir_fn: Optional[Callable[[str], List[str]]] = None
) -> Optional[str]:
    """
    Find Robot Framework test file based on rpa_key_id - pure function with injected dependencies.
    
    Args:
        rpa_key_id: RPA key identifier
        robots_base_path: Base path to rpa-robots directory
        path_exists_fn: Optional function to check path existence (for testing)
        list_dir_fn: Optional function to list directory (for testing)
        
    Returns:
        Path to .robot file or None
    """
    if path_exists_fn is None:
        path_exists_fn = os.path.exists
    if list_dir_fn is None:
        list_dir_fn = os.listdir
    
    tests_dir = os.path.join(robots_base_path, "tests")
    if not path_exists_fn(tests_dir):
        logger.warning(f"Tests directory not found: {tests_dir}")
        return None
    
    possible_names = _build_robot_file_names(rpa_key_id)
    
    for name in possible_names:
        file_path = os.path.join(tests_dir, name)
        if path_exists_fn(file_path):
            return file_path
    
    # Fallback: find any .robot file
    return _find_any_robot_file(tests_dir, rpa_key_id, path_exists_fn, list_dir_fn)


def _build_robot_file_names(rpa_key_id: str) -> List[str]:
    """Build list of possible Robot Framework file names - pure function."""
    return [
        f"{rpa_key_id}.robot",
        f"{rpa_key_id}_test.robot",
        f"test_{rpa_key_id}.robot",
    ]


def _find_any_robot_file(
    tests_dir: str,
    rpa_key_id: str,
    path_exists_fn: Callable[[str], bool],
    list_dir_fn: Callable[[str], List[str]]
) -> Optional[str]:
    """Find any .robot file in tests directory - pure function."""
    try:
        files = list_dir_fn(tests_dir)
        for file in files:
            if file.endswith('.robot'):
                file_path = os.path.join(tests_dir, file)
                logger.info(f"Using Robot Framework file: {file} for rpa_key_id: {rpa_key_id}")
                return file_path
    except OSError as e:
        logger.error(f"Error listing directory {tests_dir}: {e}")
    
    return None

