"""Unit tests for converter service."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

# Skip tests if pandas is not available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="pandas not installed")

from src.services.converter import xls_to_rpa_request


@pytest.mark.unit
class TestXlsToRpaRequest:
    """Tests for xls_to_rpa_request function."""

    def test_xls_to_rpa_request_success(self):
        """Test successful conversion of XLSX to RPA request."""
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'NOTA FISCAL': ['NF001', 'NF002', 'NF001', 'NF003'],
                'DT': ['DT001', 'DT001', 'DT002', 'DT002'],
                'Other Column': ['A', 'B', 'C', 'D']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            result = xls_to_rpa_request(tmp_path)

            assert "rpa_key_id" in result
            assert "data" in result
            assert result["rpa_key_id"] == "rpa_protocolo_devolucao"
            
            doc_transportes_list = result["data"]["doc_transportes_list"]
            assert len(doc_transportes_list) == 2  # Two unique DTs
            
            # Check DT001
            dt001 = next((dt for dt in doc_transportes_list if dt["doc_transportes"] == "DT001"), None)
            assert dt001 is not None
            assert "NF001" in dt001["nf_e"]
            assert "NF002" in dt001["nf_e"]
            
            # Check DT002
            dt002 = next((dt for dt in doc_transportes_list if dt["doc_transportes"] == "DT002"), None)
            assert dt002 is not None
            assert "NF001" in dt002["nf_e"]
            assert "NF003" in dt002["nf_e"]
        finally:
            os.unlink(tmp_path)

    def test_xls_to_rpa_request_file_not_found(self):
        """Test conversion when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            xls_to_rpa_request("/nonexistent/path/file.xlsx")

    def test_xls_to_rpa_request_missing_nota_fiscal_column(self):
        """Test conversion when NOTA FISCAL column is missing."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'DT': ['DT001', 'DT002'],
                'Other Column': ['A', 'B']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            with pytest.raises(ValueError, match="NOTA FISCAL column not found"):
                xls_to_rpa_request(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_xls_to_rpa_request_missing_dt_column(self):
        """Test conversion when DT column is missing."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'NOTA FISCAL': ['NF001', 'NF002'],
                'Other Column': ['A', 'B']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            with pytest.raises(ValueError, match="DT column not found"):
                xls_to_rpa_request(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_xls_to_rpa_request_empty_rows(self):
        """Test conversion when no rows have both DT and NOTA FISCAL."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'NOTA FISCAL': ['', '', None],
                'DT': ['', None, ''],
                'Other Column': ['A', 'B', 'C']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            with pytest.raises(ValueError, match="No rows with both DT and NOTA FISCAL values found"):
                xls_to_rpa_request(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_xls_to_rpa_request_case_insensitive_columns(self):
        """Test conversion with case-insensitive column matching."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'nota fiscal': ['NF001', 'NF002'],  # lowercase
                'dt': ['DT001', 'DT001'],  # lowercase
                'Other Column': ['A', 'B']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            result = xls_to_rpa_request(tmp_path)
            assert "data" in result
            assert len(result["data"]["doc_transportes_list"]) > 0
        finally:
            os.unlink(tmp_path)

    def test_xls_to_rpa_request_with_whitespace(self):
        """Test conversion with columns that have whitespace."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                '  NOTA FISCAL  ': ['NF001', 'NF002'],  # with whitespace
                '  DT  ': ['DT001', 'DT001'],  # with whitespace
                'Other Column': ['A', 'B']
            })
            df.to_excel(tmp_file.name, index=False)
            tmp_path = tmp_file.name

        try:
            result = xls_to_rpa_request(tmp_path)
            assert "data" in result
            assert len(result["data"]["doc_transportes_list"]) > 0
        finally:
            os.unlink(tmp_path)

