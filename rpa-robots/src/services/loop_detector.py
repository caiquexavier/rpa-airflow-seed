"""Loop detection and tracking - Functional programming style."""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class LoopType(str, Enum):
    """Loop type enumeration."""
    FOR_LOOP = "FOR_LOOP"
    WHILE_LOOP = "WHILE_LOOP"
    ARRAY_PROCESSING = "ARRAY_PROCESSING"


@dataclass(frozen=True)
class LoopContext:
    """Immutable loop context."""
    loop_step: str
    loop_type: LoopType
    total_iterations: int
    current_iteration: int = 0
    item_data: Dict[str, Any] = field(default_factory=dict)
    
    def next_iteration(self, item_data: Optional[Dict[str, Any]] = None) -> "LoopContext":
        """Create new context with next iteration (immutable)."""
        return LoopContext(
            loop_step=self.loop_step,
            loop_type=self.loop_type,
            total_iterations=self.total_iterations,
            current_iteration=self.current_iteration + 1,
            item_data=item_data or self.item_data
        )
    
    def is_complete(self) -> bool:
        """Check if loop is complete."""
        return self.current_iteration >= self.total_iterations


def detect_loop_step(step_name: str) -> bool:
    """Detect if a step is a loop processing step."""
    loop_indicators = [
        "process",
        "array",
        "foreach",
        "for",
        "loop",
        "iterate",
        "batch"
    ]
    
    step_lower = step_name.lower()
    return any(indicator in step_lower for indicator in loop_indicators)


def extract_loop_info(
    step_name: str,
    step_data: Optional[Dict[str, Any]] = None
) -> Optional[LoopContext]:
    """Extract loop information from step data."""
    if not detect_loop_step(step_name):
        return None
    
    if not step_data:
        return None
    
    array_length = None
    
    for key in ["array_length", "length", "count", "total", "size"]:
        if key in step_data:
            array_length = step_data[key]
            break
    
    if array_length is None:
        for key, value in step_data.items():
            if isinstance(value, (list, tuple)):
                array_length = len(value)
                break
    
    if array_length is None or array_length == 0:
        return None
    
    loop_type = LoopType.ARRAY_PROCESSING
    if "for" in step_name.lower():
        loop_type = LoopType.FOR_LOOP
    
    return LoopContext(
        loop_step=step_name,
        loop_type=loop_type,
        total_iterations=array_length,
        current_iteration=0,
        item_data=step_data
    )


class LoopTracker:
    """Track loop execution state."""
    
    def __init__(self):
        self._active_loops: Dict[str, LoopContext] = {}
    
    def start_loop(
        self,
        loop_step: str,
        loop_context: LoopContext
    ) -> None:
        """Start tracking a loop."""
        self._active_loops[loop_step] = loop_context
    
    def next_iteration(
        self,
        loop_step: str,
        item_data: Optional[Dict[str, Any]] = None
    ) -> Optional[LoopContext]:
        """Move to next iteration."""
        if loop_step not in self._active_loops:
            return None
        
        current = self._active_loops[loop_step]
        next_context = current.next_iteration(item_data)
        self._active_loops[loop_step] = next_context
        
        return next_context
    
    def get_loop(self, loop_step: str) -> Optional[LoopContext]:
        """Get current loop context."""
        return self._active_loops.get(loop_step)
    
    def end_loop(self, loop_step: str) -> Optional[LoopContext]:
        """End loop tracking."""
        return self._active_loops.pop(loop_step, None)
    
    def has_active_loops(self) -> bool:
        """Check if there are active loops."""
        return len(self._active_loops) > 0
