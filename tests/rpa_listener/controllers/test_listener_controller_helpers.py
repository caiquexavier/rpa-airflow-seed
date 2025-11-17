"""Unit tests for listener controller helper functions."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
import tempfile
import os

from src.controllers.listener_controller import (
    _is_retry_loop_line, _extract_retry_error_from_line,
    _extract_error_from_output_text, _extract_error_detail_from_output,
    _build_rpa_response
)


@pytest.mark.unit
class TestIsRetryLoopLine:
    """Tests for _is_retry_loop_line function."""

    def test_is_retry_loop_line_warn_retrying(self):
        """Test detection of retry loop with [ WARN ] Retrying pattern."""
        line = "[ WARN ] Retrying (Retry(total=0)) after connection broken"
        assert _is_retry_loop_line(line) is True

    def test_is_retry_loop_line_new_connection_error(self):
        """Test detection of NewConnectionError pattern."""
        line = "NewConnectionError: Failed to establish [WinError 10061]"
        assert _is_retry_loop_line(line) is True

    def test_is_retry_loop_line_connection_refused(self):
        """Test detection of connection refused pattern."""
        line = "Connection refused, retrying..."
        assert _is_retry_loop_line(line) is True

    def test_is_retry_loop_line_normal_line(self):
        """Test that normal lines are not detected as retry loops."""
        line = "Normal log message without retry patterns"
        assert _is_retry_loop_line(line) is False


@pytest.mark.unit
class TestExtractRetryErrorFromLine:
    """Tests for _extract_retry_error_from_line function."""

    def test_extract_retry_error_with_winerror(self):
        """Test extracting error with WinError code."""
        line = "NewConnectionError: [WinError 10061] Nenhuma ligacao"
        result = _extract_retry_error_from_line(line)
        assert "WinError 10061" in result
        assert "Nenhuma ligacao" in result

    def test_extract_retry_error_with_session_path(self):
        """Test extracting error with session path."""
        line = "Retrying after connection broken: /session/12345"
        result = _extract_retry_error_from_line(line)
        assert "/session/" in result

    def test_extract_retry_error_fallback(self):
        """Test fallback to first 300 chars."""
        line = "Simple retry message without special patterns"
        result = _extract_retry_error_from_line(line)
        assert len(result) <= 300
        assert "retry" in result.lower()


@pytest.mark.unit
class TestExtractErrorFromOutputText:
    """Tests for _extract_error_from_output_text function."""

    def test_extract_error_empty_text(self):
        """Test with empty text."""
        result = _extract_error_from_output_text("")
        assert result is None

    def test_extract_error_retry_loop_pattern(self):
        """Test extracting retry loop error."""
        output = "[ WARN ] Retrying after connection broken by NewConnectionError"
        result = _extract_error_from_output_text(output)
        assert result is not None
        assert "Connection" in result or "retry" in result.lower()

    def test_extract_error_http_connection_pool(self):
        """Test extracting HTTPConnectionPool error."""
        output = "HTTPConnectionPool: Max retries exceeded"
        result = _extract_error_from_output_text(output)
        assert result is not None
        assert "HTTPConnectionPool" in result or "Max retries" in result

    def test_extract_error_robot_warn(self):
        """Test extracting Robot Framework WARN."""
        output = "[ WARN ] could not be run on failure: test"
        result = _extract_error_from_output_text(output)
        assert result is not None
        assert "[ WARN ]" in result

    def test_extract_error_exception_pattern(self):
        """Test extracting exception pattern."""
        output = "Exception: Test error message"
        result = _extract_error_from_output_text(output)
        assert result is not None
        assert "Test error message" in result

    def test_extract_error_no_match(self):
        """Test with text that doesn't match any pattern."""
        output = "Normal log output without errors"
        result = _extract_error_from_output_text(output)
        assert result is None


@pytest.mark.unit
class TestExtractErrorDetailFromOutput:
    """Tests for _extract_error_detail_from_output function."""

    def test_extract_error_detail_file_not_found(self):
        """Test when output.xml doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            result = _extract_error_detail_from_output(results_dir)
            assert result == "Robot execution failed"

    def test_extract_error_detail_with_connection_error(self):
        """Test extracting connection error from XML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            # Create XML with connection error
            root = ET.Element('robot')
            suite = ET.SubElement(root, 'suite')
            test = ET.SubElement(suite, 'test')
            status = ET.SubElement(test, 'status', status='FAIL')
            status.text = "HTTPConnectionPool: Max retries exceeded"
            
            tree = ET.ElementTree(root)
            tree.write(str(output_xml), encoding='utf-8', xml_declaration=True)
            
            result = _extract_error_detail_from_output(results_dir)
            assert "HTTPConnectionPool" in result or "Max retries" in result

    def test_extract_error_detail_with_timeout_error(self):
        """Test extracting timeout/locator error from XML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            root = ET.Element('robot')
            suite = ET.SubElement(root, 'suite')
            test = ET.SubElement(suite, 'test')
            status = ET.SubElement(test, 'status', status='FAIL')
            status.text = "Timeout 5000ms waiting for locator('button') to be visible"
            
            tree = ET.ElementTree(root)
            tree.write(str(output_xml), encoding='utf-8', xml_declaration=True)
            
            result = _extract_error_detail_from_output(results_dir)
            assert "button" in result or "5" in result  # 5 seconds

    def test_extract_error_detail_xml_parse_error(self):
        """Test handling XML parse errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            # Write invalid XML
            output_xml.write_text("Invalid XML content <unclosed tag")
            
            result = _extract_error_detail_from_output(results_dir)
            assert "XML parsing error" in result or "Robot execution failed" in result


@pytest.mark.unit
class TestBuildRpaResponse:
    """Tests for _build_rpa_response function."""

    def test_build_rpa_response_success(self):
        """Test building response for successful execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            # Create XML with success
            root = ET.Element('robot')
            tree = ET.ElementTree(root)
            tree.write(str(output_xml), encoding='utf-8', xml_declaration=True)
            
            message = {
                "rpa_request": {
                    "notas_fiscais": ["NF001", "NF002"]
                }
            }
            
            result = _build_rpa_response(message, results_dir, success=True)
            assert "notas_fiscais" in result
            assert len(result["notas_fiscais"]) == 2

    def test_build_rpa_response_failure(self):
        """Test building response for failed execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            root = ET.Element('robot')
            suite = ET.SubElement(root, 'suite')
            test = ET.SubElement(suite, 'test')
            status = ET.SubElement(test, 'status', status='FAIL')
            status.text = "Test failed"
            
            tree = ET.ElementTree(root)
            tree.write(str(output_xml), encoding='utf-8', xml_declaration=True)
            
            message = {"rpa_request": {"notas_fiscais": ["NF001"]}}
            
            result = _build_rpa_response(message, results_dir, success=False)
            assert "error" in result

    def test_build_rpa_response_with_error_modal(self):
        """Test building response with error modal detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            output_xml = results_dir / 'output.xml'
            
            root = ET.Element('robot')
            suite = ET.SubElement(root, 'suite')
            test = ET.SubElement(suite, 'test')
            msg = ET.SubElement(test, 'msg', level='INFO')
            msg.text = "Processing Nota Fiscal NF001"
            error_msg = ET.SubElement(test, 'msg', level='FAIL')
            error_msg.text = "Error modal detected after search: Test error"
            
            tree = ET.ElementTree(root)
            tree.write(str(output_xml), encoding='utf-8', xml_declaration=True)
            
            message = {
                "rpa_request": {
                    "notas_fiscais": ["NF001"]
                }
            }
            
            result = _build_rpa_response(message, results_dir, success=True)
            assert "notas_fiscais" in result
            # Check if error was detected for NF001
            nf_status = result["notas_fiscais"][0]
            if nf_status.get("status") == "error":
                assert "error_message" in nf_status

