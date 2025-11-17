"""Utilities for extracting Robot Framework step results from output files."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class StepResult:
    """Represents the execution result for a top-level Robot keyword."""

    order: int
    name: str
    status: str
    message: Optional[str]
    test_name: str
    started_at: Optional[str]
    elapsed: Optional[str]

    def as_dict(self) -> dict:
        """Return a serialisable representation."""
        return {
            "order": self.order,
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "test_name": self.test_name,
            "started_at": self.started_at,
            "elapsed": self.elapsed,
        }


def extract_top_level_step_results(results_dir: Path) -> List[StepResult]:
    """
    Parse Robot Framework ``output.xml`` and return top-level keyword execution info.

    Only direct child keywords of each test case are considered so that we capture
    the business-level steps defined in the ``.robot`` file (e.g., lines 11-16 in
    ``ecargo_pod_download.robot``).
    """
    output_xml = results_dir / "output.xml"
    if not output_xml.exists():
        return []

    try:
        tree = ET.parse(str(output_xml))
    except ET.ParseError:
        return []

    root = tree.getroot()
    step_results: List[StepResult] = []

    for test in root.findall(".//test"):
        order = 1
        test_name = test.get("name", "Unknown Test")
        for kw in _iter_direct_keywords(test):
            status_node = kw.find("./status")
            status = (status_node.get("status") if status_node is not None else "UNKNOWN") or "UNKNOWN"
            message = (status_node.text or "").strip() or None if status_node is not None else None
            step_results.append(
                StepResult(
                    order=order,
                    name=kw.get("name", f"Step {order}"),
                    status=status.upper(),
                    message=message,
                    test_name=test_name,
                    started_at=status_node.get("start") if status_node is not None else None,
                    elapsed=status_node.get("elapsed") if status_node is not None else None,
                )
            )
            order += 1

    return step_results


def _iter_direct_keywords(test_node: ET.Element) -> Iterable[ET.Element]:
    """Yield direct child keyword elements for the given test node."""
    for child in test_node:
        if child.tag == "kw":
            yield child

