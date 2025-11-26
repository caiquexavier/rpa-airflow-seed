"""Tests for PdfFunctionsOperator OCR NF-e renaming.

These tests avoid real OCR by monkeypatching the extraction helper and
operate entirely on temporary files created under pytest's tmp_path.
"""

from pathlib import Path
from typing import List

from airflow.src.operators.pdf_functions_operator import PdfFunctionsOperator


def test_ocr_nf_and_rename_uses_extracted_value(tmp_path, monkeypatch):
    """Ensure _ocr_nf_and_rename renames files using the extracted NF-e value."""

    # Create a dummy PDF file (empty file is enough for the test since OCR is mocked).
    pdf_path = tmp_path / "original.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% Test content\n")

    # Monkeypatch OCR helper to avoid heavy dependencies and IO.
    def fake_extract_nf_value(path: Path) -> str:  # type: ignore[unused-argument]
        return "00012345"

    monkeypatch.setattr(
        "airflow.src.operators.pdf_functions_operator.extract_nf_value_from_pdf",
        fake_extract_nf_value,
    )

    operator = PdfFunctionsOperator(
        task_id="test_pdf_ocr",
        folder_path=str(tmp_path),
        output_dir=str(tmp_path),
        functions=["ocr_nf"],
        overwrite=True,
    )

    result_paths: List[Path] = operator._ocr_nf_and_rename([pdf_path])  # type: ignore[arg-type]

    assert len(result_paths) == 1
    renamed = result_paths[0]
    # Leading zeros should be trimmed: "00012345" -> "12345.pdf"
    assert renamed.name == "12345.pdf"
    assert renamed.exists()


