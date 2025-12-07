"""Unit tests for OCR rotation pipeline.

Tests for the clean, composable OCR rotation functions in libs/ocr_rotation.py.
"""

import pytest
import numpy as np
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from airflow.src.libs import ocr_rotation
    MODULE_AVAILABLE = True
except ImportError:
    MODULE_AVAILABLE = False

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_image_array():
    """Create a simple test image as numpy array."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")
    
    # Create a simple white image with some text-like structure
    img = Image.new('RGB', (200, 100), color='white')
    # Convert to numpy array
    return np.array(img)


@pytest.fixture
def rotated_image_array():
    """Create a rotated test image."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")
    
    img = Image.new('RGB', (100, 200), color='white')  # Portrait orientation
    return np.array(img)


class TestRotationInfo:
    """Tests for RotationInfo dataclass."""
    
    def test_rotation_info_creation(self):
        """Test creating RotationInfo with valid data."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        info = ocr_rotation.RotationInfo(angle=90.0, source="osd")
        assert info.angle == 90.0
        assert info.source == "osd"
    
    def test_rotation_info_zero_angle(self):
        """Test RotationInfo with zero angle."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        info = ocr_rotation.RotationInfo(angle=0.0, source="manual")
        assert info.angle == 0.0
        assert info.source == "manual"


class TestOcrResult:
    """Tests for OcrResult dataclass."""
    
    def test_ocr_result_creation(self):
        """Test creating OcrResult with valid data."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result = ocr_rotation.OcrResult(
            engine_name="tesseract",
            text="Sample text",
            confidence=85.5,
            rotation_applied=90.0
        )
        assert result.engine_name == "tesseract"
        assert result.text == "Sample text"
        assert result.confidence == 85.5
        assert result.rotation_applied == 90.0
    
    def test_ocr_result_no_confidence(self):
        """Test OcrResult with None confidence."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result = ocr_rotation.OcrResult(
            engine_name="tesseract",
            text="Sample text",
            confidence=None,
            rotation_applied=0.0
        )
        assert result.confidence is None


class TestImageConversion:
    """Tests for PIL/numpy conversion functions."""
    
    def test_pil_to_numpy(self, sample_image_array):
        """Test converting PIL Image to numpy array."""
        if not MODULE_AVAILABLE or not PIL_AVAILABLE:
            pytest.skip("Module or PIL not available")
        
        pil_image = Image.fromarray(sample_image_array)
        result = ocr_rotation.pil_to_numpy(pil_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == sample_image_array.shape
    
    def test_numpy_to_pil(self, sample_image_array):
        """Test converting numpy array to PIL Image."""
        if not MODULE_AVAILABLE or not PIL_AVAILABLE:
            pytest.skip("Module or PIL not available")
        
        result = ocr_rotation.numpy_to_pil(sample_image_array)
        assert isinstance(result, Image.Image)
        assert result.size == (sample_image_array.shape[1], sample_image_array.shape[0])


class TestRotateImageOpenCV:
    """Tests for OpenCV rotation function."""
    
    def test_rotate_image_zero_angle(self, sample_image_array):
        """Test rotating image by 0° (no change)."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        if not ocr_rotation.CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        result = ocr_rotation.rotate_image_opencv(sample_image_array, 0.0)
        assert isinstance(result, np.ndarray)
        # Image should be similar (allowing for minor differences due to interpolation)
        assert result.shape[0] == sample_image_array.shape[0]
        assert result.shape[1] == sample_image_array.shape[1]
    
    def test_rotate_image_90_degrees(self, sample_image_array):
        """Test rotating image by 90°."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        if not ocr_rotation.CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        original_shape = sample_image_array.shape
        result = ocr_rotation.rotate_image_opencv(sample_image_array, 90.0)
        assert isinstance(result, np.ndarray)
        # After 90° rotation, dimensions should swap
        assert result.shape[0] == original_shape[1]
        assert result.shape[1] == original_shape[0]


class TestCoarseRotate:
    """Tests for coarse rotation detection."""
    
    def test_coarse_rotate_no_tesseract(self, sample_image_array, monkeypatch):
        """Test coarse_rotate when Tesseract is not available."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        # Mock Tesseract as unavailable
        monkeypatch.setattr(ocr_rotation, "TESSERACT_AVAILABLE", False)
        
        result_image, rotation_info = ocr_rotation.coarse_rotate(sample_image_array)
        
        assert isinstance(result_image, np.ndarray)
        assert rotation_info.angle == 0.0
        assert rotation_info.source == "manual"
    
    def test_coarse_rotate_returns_image_and_info(self, sample_image_array):
        """Test that coarse_rotate returns both image and RotationInfo."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result_image, rotation_info = ocr_rotation.coarse_rotate(sample_image_array)
        
        assert isinstance(result_image, np.ndarray)
        assert isinstance(rotation_info, ocr_rotation.RotationInfo)
        assert rotation_info.angle >= 0.0
        assert rotation_info.angle < 360.0


class TestDeskewImage:
    """Tests for deskew functionality."""
    
    def test_deskew_image_no_opencv(self, sample_image_array, monkeypatch):
        """Test deskew when OpenCV is not available."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        monkeypatch.setattr(ocr_rotation, "CV2_AVAILABLE", False)
        
        result_image, skew_angle = ocr_rotation.deskew_image(sample_image_array)
        
        assert isinstance(result_image, np.ndarray)
        assert skew_angle == 0.0
    
    def test_deskew_image_returns_image_and_angle(self, sample_image_array):
        """Test that deskew_image returns both image and angle."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result_image, skew_angle = ocr_rotation.deskew_image(sample_image_array)
        
        assert isinstance(result_image, np.ndarray)
        assert isinstance(skew_angle, float)
        # Skew angle should be small (typically < 45°)
        assert abs(skew_angle) <= 45.0


class TestSelectBestOcrResult:
    """Tests for OCR result selection logic."""
    
    def test_select_best_empty_list(self):
        """Test selecting best from empty list."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result = ocr_rotation.select_best_ocr_result([])
        assert result.engine_name == "none"
        assert result.text == ""
    
    def test_select_best_single_result(self):
        """Test selecting best from single result."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        results = [
            ocr_rotation.OcrResult(
                engine_name="tesseract",
                text="Sample text",
                confidence=85.0,
                rotation_applied=0.0
            )
        ]
        
        best = ocr_rotation.select_best_ocr_result(results)
        assert best.engine_name == "tesseract"
        assert best.text == "Sample text"
    
    def test_select_best_by_confidence(self):
        """Test selecting best result by confidence."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        results = [
            ocr_rotation.OcrResult(
                engine_name="tesseract",
                text="Text 1",
                confidence=70.0,
                rotation_applied=0.0
            ),
            ocr_rotation.OcrResult(
                engine_name="paddleocr",
                text="Text 2",
                confidence=90.0,
                rotation_applied=0.0
            )
        ]
        
        best = ocr_rotation.select_best_ocr_result(results)
        assert best.engine_name == "paddleocr"
        assert best.confidence == 90.0
    
    def test_select_best_by_text_length_when_no_confidence(self):
        """Test selecting best result by text length when confidence unavailable."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        results = [
            ocr_rotation.OcrResult(
                engine_name="tesseract",
                text="Short",
                confidence=None,
                rotation_applied=0.0
            ),
            ocr_rotation.OcrResult(
                engine_name="paddleocr",
                text="Much longer text here",
                confidence=None,
                rotation_applied=0.0
            )
        ]
        
        best = ocr_rotation.select_best_ocr_result(results)
        assert best.engine_name == "paddleocr"
        assert len(best.text) > len(results[0].text)
    
    def test_select_best_prefers_non_empty(self):
        """Test that non-empty results are preferred over empty ones."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        results = [
            ocr_rotation.OcrResult(
                engine_name="tesseract",
                text="",
                confidence=100.0,
                rotation_applied=0.0
            ),
            ocr_rotation.OcrResult(
                engine_name="paddleocr",
                text="Some text",
                confidence=50.0,
                rotation_applied=0.0
            )
        ]
        
        best = ocr_rotation.select_best_ocr_result(results)
        assert best.engine_name == "paddleocr"
        assert best.text == "Some text"
    
    def test_select_best_tiebreak_prefers_tesseract(self):
        """Test that Tesseract is preferred in case of tie."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        results = [
            ocr_rotation.OcrResult(
                engine_name="paddleocr",
                text="Same length text",
                confidence=None,
                rotation_applied=0.0
            ),
            ocr_rotation.OcrResult(
                engine_name="tesseract",
                text="Same length text",
                confidence=None,
                rotation_applied=0.0
            )
        ]
        
        best = ocr_rotation.select_best_ocr_result(results)
        assert best.engine_name == "tesseract"


class TestProcessImage:
    """Tests for full image processing pipeline."""
    
    def test_process_image_returns_result(self, sample_image_array):
        """Test that process_image returns ProcessedDocumentResult."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result = ocr_rotation.process_image(
            sample_image_array,
            lang="eng",
            use_paddleocr=False,
            use_easyocr=False
        )
        
        assert isinstance(result, ocr_rotation.ProcessedDocumentResult)
        assert isinstance(result.text, str)
        assert isinstance(result.engine_used, str)
        assert isinstance(result.coarse_rotation_angle, float)
        assert isinstance(result.deskew_angle, float)
        assert isinstance(result.all_engine_results, list)
    
    def test_process_image_tracks_rotation(self, sample_image_array):
        """Test that process_image tracks rotation angles."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result = ocr_rotation.process_image(
            sample_image_array,
            lang="eng",
            use_paddleocr=False
        )
        
        # Total rotation should be sum of coarse and deskew
        total_rotation = result.coarse_rotation_angle + result.deskew_angle
        
        # Check that all engine results have correct rotation tracking
        for ocr_result in result.all_engine_results:
            assert abs(ocr_result.rotation_applied - total_rotation) < 0.1


class TestProcessImageWithVerification:
    """Tests for process_image_with_verification."""
    
    def test_process_image_with_verification_returns_checks(self, sample_image_array):
        """Test that verification function returns landscape and inverted checks."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        result, is_landscape, is_inverted = ocr_rotation.process_image_with_verification(
            sample_image_array,
            lang="eng",
            use_paddleocr=False,
            require_landscape=True,
            check_inverted=True
        )
        
        assert isinstance(result, ocr_rotation.ProcessedDocumentResult)
        assert isinstance(is_landscape, bool)
        assert isinstance(is_inverted, bool)
    
    def test_process_image_with_verification_landscape_check(self, rotated_image_array):
        """Test landscape check on portrait image."""
        if not MODULE_AVAILABLE:
            pytest.skip("Module not available")
        
        # rotated_image_array is portrait (100x200)
        result, is_landscape, _ = ocr_rotation.process_image_with_verification(
            rotated_image_array,
            lang="eng",
            use_paddleocr=False,
            require_landscape=True,
            check_inverted=False
        )
        
        # Portrait image should not be landscape
        assert is_landscape is False

