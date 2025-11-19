"""GPT PDF service - Unified service that rotates PDF and extracts all data using GPT."""
import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from ...config.config import get_openai_api_key, get_openai_model_name
from openai import OpenAI

logger = logging.getLogger(__name__)


def gpt_pdf_extractor(
    file_path: str, 
    output_path: Optional[str] = None,
    fields: Optional[list[str]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Rotate PDF to readable position and extract all data using GPT in a single operation.
    
    This function:
    1. Tests different rotations (0, 90, 180, 270 degrees)
    2. Uses GPT to determine the best rotation AND extract all identifiable data in one prompt
    3. Applies the rotation to the PDF
    4. Saves the rotated PDF to output_path
    5. Copies the file to organized folder based on extracted fields (doc_transportes and nf_e):
       - Creates folder: {doc_transportes}/
       - Copies file to: {doc_transportes}/{nf_e}.pdf (original file is kept in place)
       - Trims leading zeros from nf_e
    6. Returns the copied file path and extracted JSON data
    
    Args:
        file_path: Path to PDF file to process
        output_path: Optional path to save rotated PDF. If None, overwrites original file.
        fields: Optional list of specific fields to extract. If None, extracts all identifiable fields.
        
    Returns:
        Tuple of (organized_file_path, extracted_data_dict)
        Note: organized_file_path may be the same as output_path if required fields are missing.
        
    Raises:
        FileNotFoundError: If PDF file does not exist
        RuntimeError: If processing fails or PyMuPDF is not available
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) not available. Install pymupdf to use PDF rotation.")
    
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    logger.info(f"Rotating and extracting data from PDF using GPT: {file_path}")
    
    # Determine output path
    if output_path is None:
        output_path = file_path
    else:
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(file_path)
    try:
        if len(doc) == 0:
            logger.warning("PDF has no pages, skipping processing")
            return file_path, {}
        
        # Step 1: Use OCR to rotate PDF to readable position (left to right)
        logger.info(f"Processing PDF with {len(doc)} pages")
        first_page = doc[0]
        current_rotation = first_page.rotation % 360
        logger.info(f"First page current rotation: {current_rotation}°")
        
        # Use OCR to determine correct rotation
        best_rotation = _determine_rotation_with_ocr(first_page)
        logger.info(f"OCR determined best rotation: {best_rotation}°")
        
        # Calculate rotation needed to reach best_rotation
        # best_rotation is the absolute rotation the page should have (0, 90, 180, or 270)
        rotation_needed = (best_rotation - current_rotation) % 360
        
        # Always apply rotation to ensure consistency (even if rotation_needed is 0, verify it's correct)
        logger.info(f"Applying rotation: current={current_rotation}°, target={best_rotation}°, needed={rotation_needed}°")
        
        if rotation_needed == 0 and current_rotation == best_rotation:
            logger.info("PDF is already in readable position, no rotation needed")
        else:
            logger.info(f"Rotating all {len(doc)} pages by {rotation_needed}° to reach {best_rotation}°")
            for page_num in range(len(doc)):
                page = doc[page_num]
                original_rotation = page.rotation % 360
                
                # Calculate new rotation: add rotation_needed to current
                new_rotation = (original_rotation + rotation_needed) % 360
                
                # Ensure we're setting to best_rotation (absolute value)
                # This handles edge cases where calculation might be off
                if new_rotation != best_rotation:
                    logger.warning(f"Page {page_num + 1}: Calculated rotation {new_rotation}° doesn't match target {best_rotation}°, forcing to target")
                    new_rotation = best_rotation
                
                page.set_rotation(new_rotation)
                
                # Verify rotation was set correctly
                actual_rotation = page.rotation % 360
                if actual_rotation != new_rotation:
                    logger.error(f"Page {page_num + 1}: Failed to set rotation! Expected {new_rotation}°, got {actual_rotation}°")
                    # Force set again
                    page.set_rotation(best_rotation)
                    actual_rotation = page.rotation % 360
                    logger.info(f"Page {page_num + 1}: Force set rotation to {actual_rotation}°")
                else:
                    logger.info(f"Page {page_num + 1}: rotated from {original_rotation}° to {new_rotation}° ✓")
        
        # Step 2: Use GPT Vision to extract data from rotated PDF
        logger.info("Extracting data using GPT Vision from rotated PDF")
        
        # Render all pages for GPT Vision (now at correct rotation)
        all_pages_images = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            base64_image = _render_page_to_base64_image(page, 0)  # Render at current rotation
            if base64_image:
                all_pages_images.append(base64_image)
                logger.info(f"Rendered page {page_num + 1} as image for GPT extraction")
        
        # Use GPT Vision to extract data
        extracted_data = _ask_gpt_vision_for_data_extraction(
            all_pages_images,
            fields
        )
        
        # Save rotated PDF - force rewrite to ensure rotation is persisted
        temp_file = output_path + ".tmp"
        try:
            # Use garbage=4 to ensure all changes are written
            doc.save(temp_file, garbage=4, deflate=True, incremental=False, encryption=fitz.PDF_ENCRYPT_KEEP)
            
            # Verify the file was created
            if not Path(temp_file).exists():
                raise RuntimeError(f"Temporary file was not created: {temp_file}")
            
            # Move to final location
            shutil.move(temp_file, output_path)
            
            # Verify final file exists and has content
            if not Path(output_path).exists():
                raise RuntimeError(f"Output file was not created: {output_path}")
            
            file_size = Path(output_path).stat().st_size
            if file_size == 0:
                raise RuntimeError(f"Output file is empty: {output_path}")
            
            logger.info(f"Successfully saved rotated PDF to: {output_path} ({file_size} bytes)")
            
            # Verify rotation was applied by checking first page
            verify_doc = fitz.open(output_path)
            try:
                first_page_rotation = verify_doc[0].rotation % 360
                expected_rotation = best_rotation if rotation_needed != 0 else current_rotation
                logger.info(f"Verification: First page rotation in saved file: {first_page_rotation}° (expected: {expected_rotation}°)")
                if first_page_rotation != expected_rotation:
                    logger.warning(f"Rotation mismatch! Expected {expected_rotation}° but got {first_page_rotation}°")
                else:
                    logger.info(f"✓ Rotation verified: PDF is now at {first_page_rotation}° (readable position)")
            finally:
                verify_doc.close()
                
        except Exception as e:
            if Path(temp_file).exists():
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to save rotated PDF: {e}") from e
        
        if rotation_needed == 0:
            logger.info("PDF is already in readable position, no rotation needed")
        else:
            logger.info(f"✓ PDF rotated by {rotation_needed}° to {best_rotation}° - should now be in readable position (left to right)")
        
        # Step 3: Organize file based on extracted fields
        organized_file_path = _organize_file_by_extracted_fields(output_path, extracted_data)
        
        return organized_file_path, extracted_data
        
    finally:
        doc.close()


def _determine_rotation_with_ocr(page) -> int:
    """
    Convert PDF page to image, then use OCR to determine the correct rotation.
    Tests all rotations (0°, 90°, 180°, 270°) on the image and returns the one with most readable text.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        Best rotation angle (0, 90, 180, or 270)
    """
    if not TESSERACT_AVAILABLE:
        logger.warning("Tesseract OCR not available, defaulting to 0° rotation")
        return 0
    
    import io
    
    # Step 1: Convert PDF page to image (at current rotation)
    logger.info("Converting PDF page to image for rotation detection...")
    original_rotation = page.rotation
    
    try:
        # Render page to image at current rotation
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        base_image = Image.open(io.BytesIO(img_data))
        logger.info(f"Converted page to image: {base_image.size[0]}x{base_image.size[1]} pixels")
    except Exception as e:
        logger.error(f"Failed to convert page to image: {e}")
        return 0
    
    # Step 2: Test all rotations on the IMAGE (not the page)
    rotations = [0, 90, 180, 270]
    rotation_scores = {}
    
    logger.info("Testing image rotations with OCR to find readable position (left to right)...")
    
    for rotation in rotations:
        try:
            # Rotate the IMAGE (not the page)
            if rotation == 0:
                test_image = base_image
            else:
                # Rotate image counter-clockwise (negative angle)
                test_image = base_image.rotate(-rotation, expand=True)
            
            # Perform OCR on rotated image
            try:
                ocr_text = pytesseract.image_to_string(
                    test_image, lang='por+eng', config='--oem 3 --psm 6'
                )
            except Exception:
                ocr_text = pytesseract.image_to_string(
                    test_image, lang='eng', config='--oem 3 --psm 6'
                )
            
            # Score based on readable text (left to right)
            text_clean = ocr_text.strip()
            word_count = len(text_clean.split()) if text_clean else 0
            char_count = len([c for c in text_clean if c.isalnum()])
            
            # Check for readable patterns
            has_numbers = any(c.isdigit() for c in text_clean)
            has_letters = any(c.isalpha() for c in text_clean)
            
            # Use Tesseract OSD (Orientation and Script Detection) for better accuracy
            osd_rotation = None
            osd_confidence = 0
            try:
                osd = pytesseract.image_to_osd(test_image, output_type=pytesseract.Output.DICT)
                osd_rotation = osd.get('rotate', 0)
                osd_confidence = osd.get('script_conf', 0)
                logger.debug(f"Image rotation {rotation}°: OSD detected rotation {osd_rotation}° (confidence: {osd_confidence})")
            except Exception as e:
                logger.debug(f"OSD detection failed for rotation {rotation}°: {e}")
            
            # Score based on OSD and text content
            # OSD returns rotation needed to make text upright (0, 90, 180, 270)
            # If OSD says 0° is needed, this image rotation is correct (text is already upright)
            if osd_rotation is not None and osd_confidence > 1.0:
                if osd_rotation == 0:
                    # This rotation makes text upright - highest priority
                    score = 10000 + word_count * 10 + char_count
                    logger.info(f"Image rotation {rotation}°: OSD confirms text is upright (confidence: {osd_confidence:.2f})")
                else:
                    # OSD says more rotation is needed - lower score
                    score = word_count * 10 + char_count - (osd_rotation * 10)
            else:
                # Fallback to word/char count scoring
                score = word_count * 10 + char_count
            
            # Additional scoring based on content
            if has_numbers and has_letters:
                score += 100  # Bonus for mixed content
            if word_count > 5:
                score += 50  # Bonus for substantial text
            
            # Penalty for very short text (likely wrong rotation)
            if word_count < 3:
                score = max(0, score - 200)
            
            rotation_scores[rotation] = score
            logger.info(f"Image rotation {rotation}°: {word_count} words, {char_count} chars, score: {score}")
            
        except Exception as e:
            logger.warning(f"Failed to test image rotation {rotation}°: {e}")
            rotation_scores[rotation] = 0
    
    # Find rotation with highest score
    best_rotation = max(rotation_scores.items(), key=lambda x: x[1])[0]
    best_score = rotation_scores[best_rotation]
    
    logger.info(f"OCR determined best rotation: {best_rotation}° (score: {best_score})")
    logger.info(f"This means the page should be rotated by {best_rotation}° to be readable (left to right)")
    
    return best_rotation


def _render_page_to_base64_image(page, image_rotation: int = 0) -> Optional[str]:
    """
    Render PDF page to base64-encoded PNG image for GPT Vision API.
    
    Renders the page at its CURRENT rotation, then rotates the IMAGE (not the page).
    This ensures we're showing GPT what the page actually looks like at different orientations.
    
    Args:
        page: PyMuPDF page object (at its current rotation)
        image_rotation: Rotation to apply to the rendered IMAGE (0, 90, 180, 270)
        
    Returns:
        Base64-encoded image string or None if failed
    """
    import base64
    import io
    
    if not PIL_AVAILABLE:
        logger.warning("PIL not available, cannot render page to image")
        return None
    
    try:
        # Render page at its CURRENT rotation (don't modify page rotation)
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # If we need to rotate the image, do it on the PIL Image, not the page
        if image_rotation != 0:
            image = Image.open(io.BytesIO(img_data))
            # Rotate image (counter-clockwise, so we use negative)
            rotated_image = image.rotate(-image_rotation, expand=True)
            # Convert back to bytes
            img_buffer = io.BytesIO()
            rotated_image.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
        
        # Convert to base64
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        return base64_image
    except Exception as e:
        logger.error(f"Failed to render page to image: {e}")
        return None


def _extract_texts_at_all_rotations(page, page_num: int = 0) -> Dict[int, str]:
    """
    Extract text from a page at all rotation angles using multiple extraction methods.
    Falls back to OCR if text extraction returns empty (for image-based PDFs).
    
    Args:
        page: PyMuPDF page object
        page_num: Page number for logging (0-indexed)
        
    Returns:
        Dictionary mapping rotation degrees to extracted text
    """
    import io
    
    rotations = [0, 90, 180, 270]
    rotation_texts: Dict[int, str] = {}
    original_rotation = page.rotation
    
    for rotation in rotations:
        try:
            page.set_rotation(rotation)
            
            # Try multiple text extraction methods for better results
            text = ""
            
            # Method 1: Standard get_text() - works for text-based PDFs
            try:
                text = page.get_text()
                if text:
                    text = text.strip()
            except Exception as e:
                logger.debug(f"Page {page_num + 1}, rotation {rotation}°: get_text() failed: {e}")
            
            # Method 2: get_text("text") with layout preservation - better for complex layouts
            if not text or len(text.strip()) < 10:
                try:
                    text_layout = page.get_text("text")
                    if text_layout and len(text_layout.strip()) > len(text.strip()):
                        text = text_layout.strip()
                except Exception:
                    pass
            
            # Method 3: get_text("dict") - structured extraction
            if not text or len(text.strip()) < 10:
                try:
                    text_dict = page.get_text("dict")
                    if text_dict and "blocks" in text_dict:
                        extracted_parts = []
                        for block in text_dict.get("blocks", []):
                            if "lines" in block:
                                for line in block["lines"]:
                                    if "spans" in line:
                                        for span in line["spans"]:
                                            if "text" in span:
                                                extracted_parts.append(span["text"])
                        if extracted_parts:
                            text = " ".join(extracted_parts).strip()
                except Exception:
                    pass
            
            rotation_texts[rotation] = text if text else ""
            
        except Exception as e:
            logger.warning(f"Page {page_num + 1}, rotation {rotation}°: Failed to extract text: {e}")
            rotation_texts[rotation] = ""
        finally:
            page.set_rotation(original_rotation)
    
    return rotation_texts


def _save_llm_execution_result(
    request_timestamp: str,
    response_timestamp: str,
    model: str,
    prompt_length: int,
    prompt_preview: str,
    response_content: str,
    usage: Dict[str, Any]
) -> None:
    """
    Save LLM execution results to a file for debugging and analysis.
    
    Args:
        request_timestamp: ISO timestamp of the request
        response_timestamp: ISO timestamp of the response
        model: Model name used
        prompt_length: Length of the prompt in characters
        prompt_preview: First 500 chars of the prompt
        response_content: Full response content from LLM
        usage: Token usage information
    """
    try:
        # Create results directory if it doesn't exist
        results_dir = Path("/tmp/llm_execution_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        timestamp_str = request_timestamp.replace(":", "-").replace(".", "-")
        filename = results_dir / f"llm_result_{timestamp_str}.json"
        
        # Prepare result data
        result_data = {
            "request_timestamp": request_timestamp,
            "response_timestamp": response_timestamp,
            "model": model,
            "prompt_length": prompt_length,
            "prompt_preview": prompt_preview,
            "response_content": response_content,
            "usage": usage,
            "duration_seconds": (
                datetime.fromisoformat(response_timestamp.replace("Z", "+00:00")) -
                datetime.fromisoformat(request_timestamp.replace("Z", "+00:00"))
            ).total_seconds() if "Z" in request_timestamp else None
        }
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved LLM execution result to: {filename}")
    except Exception as e:
        logger.warning(f"Failed to save LLM execution result: {e}")


def _ask_gpt_vision_for_rotation_and_extraction(
    rotation_images: Dict[int, Optional[str]],
    all_pages_images: list[Optional[str]],
    fields: Optional[list[str]] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Ask GPT Vision to determine best rotation AND extract all data from PDF images.
    
    Args:
        rotation_images: Dictionary mapping rotation degrees to base64-encoded images (first page)
        all_pages_images: List of base64-encoded images for all pages (at best rotation)
        fields: Optional list of specific fields to extract
        
    Returns:
        Tuple of (best_rotation_degrees, extracted_data_dict)
    """
    api_key = get_openai_api_key()
    model_name = get_openai_model_name()
    client = OpenAI(api_key=api_key)
    
    # Ensure model supports vision (gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.)
    if not any(vision_model in model_name.lower() for vision_model in ['gpt-4o', 'gpt-4-turbo', 'gpt-4-vision']):
        logger.warning(f"Model {model_name} may not support vision. Using anyway...")
    
    # Build extraction instruction
    if fields and len(fields) > 0:
        fields_str = ", ".join(fields)
        extraction_instruction = f"Extract the following specific fields: {fields_str}."
    else:
        extraction_instruction = (
            "Extract ALL identifiable and relevant fields from the document. "
            "Identify common document fields such as: CNPJ, CPF, invoice numbers, dates, amounts, "
            "values, names, addresses, company names, plate numbers, quantities, etc. "
            "Use descriptive field names in lowercase with underscores (e.g., cnpj, valor_total, data_emissao)."
        )
    
    # Build messages with images for rotation detection (first page at different rotations)
    rotation_detection_content = [
        {
            "type": "text",
            "text": (
                "You are analyzing a PDF document page that may be rotated incorrectly. "
                "Below are 4 images of the same page at different rotations (0°, 90°, 180°, 270°). "
                "Your task is to:\n"
                "1. Determine which rotation produces the most readable/oriented text\n"
                "2. Analyze the best-oriented image and extract all identifiable data\n\n"
                f"{extraction_instruction}\n\n"
                "IMPORTANT:\n"
                "- Only extract data that is ACTUALLY visible in the images\n"
                "- Do NOT invent or guess field values - only extract what you can clearly see\n"
                "- If a field is not visible, do NOT include it in extracted_data\n\n"
                "Return a JSON object with:\n"
                "- 'best_rotation': The rotation angle (0, 90, 180, or 270) that produces the most readable text\n"
                "- 'rotation_reason': Brief explanation of why this rotation is best\n"
                "- 'extracted_data': A JSON object containing all fields visible in the best-oriented image"
            )
        }
    ]
    
    # Add rotation images
    for rotation in [0, 90, 180, 270]:
        base64_image = rotation_images.get(rotation)
        if base64_image:
            rotation_detection_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high"
                }
            })
            rotation_detection_content.append({
                "type": "text",
                "text": f"Image at {rotation}° rotation"
            })
    
    # If we have multiple pages, add them for complete data extraction
    if len(all_pages_images) > 1:
        rotation_detection_content.append({
            "type": "text",
            "text": f"\n\nAdditionally, here are all {len(all_pages_images)} pages of the document at the correct orientation. Extract data from ALL pages:"
        })
        for page_num, base64_image in enumerate(all_pages_images, 1):
            if base64_image:
                rotation_detection_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    }
                })
                rotation_detection_content.append({
                    "type": "text",
                    "text": f"Page {page_num}"
                })
    
    try:
        logger.info(f"Calling OpenAI Vision model {model_name} to determine rotation and extract data")
        
        # Log request details
        request_timestamp = datetime.utcnow().isoformat()
        num_images = sum(1 for img in rotation_images.values() if img) + sum(1 for img in all_pages_images if img)
        logger.info(f"LLM Vision Request - Model: {model_name}, Images: {num_images}, Timestamp: {request_timestamp}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a PDF document analyzer with vision capabilities. Always return valid JSON. "
                        "Analyze images of PDF pages at different rotations to determine the best orientation "
                        "and extract all relevant data. CRITICAL: Only extract data that is ACTUALLY visible in the images. "
                        "Do NOT invent, guess, or create example values."
                    )
                },
                {
                    "role": "user",
                    "content": rotation_detection_content
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Log response details
        response_timestamp = datetime.utcnow().isoformat()
        usage = response.usage
        logger.info(
            f"LLM Response - Model: {model_name}, "
            f"Tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}, "
            f"Timestamp: {response_timestamp}"
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Save LLM execution results for debugging
        prompt_text = json.dumps(rotation_detection_content, indent=2, default=str)[:1000]  # Preview of content
        # Extract usage info safely (handle CompletionTokensDetails)
        usage_dict = {
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(usage, 'completion_tokens', 0),
            "total_tokens": getattr(usage, 'total_tokens', 0)
        }
        _save_llm_execution_result(
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            model=model_name,
            prompt_length=len(str(rotation_detection_content)),
            prompt_preview=prompt_text + "..." if len(prompt_text) > 1000 else prompt_text,
            response_content=content,
            usage=usage_dict
        )
        
        result = json.loads(content)
        
        # Extract rotation
        best_rotation = result.get("best_rotation", 0)
        if best_rotation not in [0, 90, 180, 270]:
            logger.warning(f"Invalid rotation from GPT: {best_rotation}, defaulting to 0")
            best_rotation = 0
        
        rotation_reason = result.get("rotation_reason", "No reason provided")
        logger.info(f"GPT selected rotation {best_rotation}°: {rotation_reason}")
        
        # Extract data
        extracted_data = result.get("extracted_data", {})
        if not isinstance(extracted_data, dict):
            logger.warning("extracted_data is not a dictionary, using empty dict")
            extracted_data = {}
        
        logger.info(f"GPT extracted {len(extracted_data)} fields")
        
        return best_rotation, extracted_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        logger.warning("Defaulting to 0° rotation and empty data")
        return 0, {}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        logger.warning("Defaulting to 0° rotation and empty data")
        return 0, {}


def _organize_file_by_extracted_fields(
    file_path: str,
    extracted_data: Dict[str, Any]
) -> str:
    """
    Copy PDF file to organized folder based on extracted fields (doc_transportes and nf_e).
    
    Creates folder structure: {doc_transportes}/{nf_e}.pdf
    where nf_e has leading zeros trimmed.
    The original file is kept in place; a copy is created in the organized folder.
    
    Args:
        file_path: Current path to the PDF file
        extracted_data: Dictionary with extracted fields from GPT
        
    Returns:
        New file path after organization (copy location), or original path if fields are missing
    """
    try:
        # Extract required fields (strict: only doc_transportes/doc_transporte + nf_e variants)
        doc_transportes = extracted_data.get("doc_transportes") or extracted_data.get("doc_transporte")
        nf_e = extracted_data.get("nf_e") or extracted_data.get("nf") or extracted_data.get("nota_fiscal")
        
        # Check if both fields are available
        if not doc_transportes or not nf_e:
            logger.warning(
                f"Cannot organize file: missing required fields. "
                f"doc_transportes={doc_transportes}, nf_e={nf_e}. "
                f"Available fields: {list(extracted_data.keys())}"
            )
            return file_path
        
        # Convert to string and clean
        doc_transportes = str(doc_transportes).strip()
        nf_e = str(nf_e).strip()
        
        # Trim leading zeros from nf_e
        nf_e_trimmed = nf_e.lstrip('0') or '0'  # Keep at least one '0' if all are zeros
        
        # Sanitize folder and file names (remove invalid characters)
        doc_transportes_clean = re.sub(r'[<>:"/\\|?*]', '_', doc_transportes)
        nf_e_clean = re.sub(r'[<>:"/\\|?*]', '_', nf_e_trimmed)
        
        # Build new path structure: {doc_transportes}/{nf_e}.pdf
        # Normalize paths to handle Windows/Linux differences
        original_file = Path(file_path)
        
        # Resolve to absolute path, but handle case where file might not exist
        try:
            original_file = original_file.resolve()
        except (OSError, RuntimeError):
            # If resolve fails, use the path as-is
            original_file = Path(file_path).absolute()
        
        base_dir = original_file.parent
        new_folder = base_dir / doc_transportes_clean
        new_filename = f"{nf_e_clean}.pdf"
        new_file_path = new_folder / new_filename
        
        logger.info(f"Organizing file - Source: {original_file}, Target: {new_file_path}")
        
        # Create folder if it doesn't exist
        try:
            new_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created/organized folder: {new_folder}")
        except Exception as e:
            logger.error(f"Failed to create folder {new_folder}: {e}")
            return file_path
        
        # Normalize paths for comparison (use absolute paths)
        original_path_str = str(original_file.absolute())
        new_path_str = str(new_file_path.absolute())
        
        # Copy file to new location (keep original in place)
        if original_path_str != new_path_str:
            # Ensure source file exists before copying
            if not original_file.exists():
                logger.error(f"Source file does not exist: {original_file}")
                return file_path
            
            # Check if target file already exists
            if new_file_path.exists():
                logger.warning(f"Target file already exists: {new_file_path}. Overwriting...")
                try:
                    new_file_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to remove existing target file: {e}")
                    return file_path
            
            # Perform the copy (copy2 preserves metadata)
            try:
                shutil.copy2(str(original_file), str(new_file_path))
                logger.info(f"Copied file to organized location: {original_file} -> {new_file_path}")
            except Exception as e:
                logger.error(f"Failed to copy file: {e}")
                logger.error(f"  Source exists: {original_file.exists()}, Source: {original_file}")
                logger.error(f"  Target parent exists: {new_file_path.parent.exists()}, Target: {new_file_path}")
                return file_path
            
            # Verify the copy was successful
            if new_file_path.exists() and new_file_path.stat().st_size > 0:
                logger.info(f"✓ File successfully copied to: {new_file_path} ({new_file_path.stat().st_size} bytes)")
            else:
                logger.error(f"✗ File copy verification failed - target does not exist or is empty: {new_file_path}")
                return file_path
        else:
            logger.info(f"File already at organized location: {new_file_path}")
        
        return str(new_file_path.absolute())
        
    except Exception as e:
        logger.error(f"Failed to organize file based on extracted fields: {e}")
        logger.warning(f"Returning original file path: {file_path}")
        return file_path


def _ask_gpt_vision_for_data_extraction(
    all_pages_images: list[Optional[str]],
    fields: Optional[list[str]] = None
) -> Dict[str, Any]:
    """
    Ask GPT Vision to extract data from PDF images (rotation already determined).
    
    Args:
        all_pages_images: List of base64-encoded images for all pages (already rotated correctly)
        fields: Optional list of specific fields to extract
        
    Returns:
        Dictionary with extracted data
    """
    api_key = get_openai_api_key()
    model_name = get_openai_model_name()
    client = OpenAI(api_key=api_key)
    
    # Build extraction instruction
    if fields and len(fields) > 0:
        fields_str = ", ".join(fields)
        extraction_instruction = f"Extract the following specific fields: {fields_str}."
    else:
        extraction_instruction = (
            "Extract ALL identifiable and relevant fields from the document. "
            "Identify common document fields such as: CNPJ, CPF, invoice numbers, dates, amounts, "
            "values, names, addresses, company names, plate numbers, quantities, etc. "
            "Use descriptive field names in lowercase with underscores (e.g., cnpj, valor_total, data_emissao)."
        )
    
    # Build content with all page images
    extraction_content = [
        {
            "type": "text",
            "text": (
                "You are analyzing a PDF document that is already in the correct orientation (readable left to right). "
                f"Extract all identifiable data from the document images below.\n\n"
                f"{extraction_instruction}\n\n"
                "IMPORTANT:\n"
                "- Only extract data that is ACTUALLY visible in the images\n"
                "- Do NOT invent or guess field values - only extract what you can clearly see\n"
                "- If a field is not visible, do NOT include it in extracted_data\n\n"
                "Return a JSON object with:\n"
                "- 'extracted_data': A JSON object containing all fields visible in the images"
            )
        }
    ]
    
    # Add all page images
    for page_num, base64_image in enumerate(all_pages_images, 1):
        if base64_image:
            extraction_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high"
                }
            })
            extraction_content.append({
                "type": "text",
                "text": f"Page {page_num}"
            })
    
    try:
        logger.info(f"Calling OpenAI Vision model {model_name} to extract data from {len(all_pages_images)} pages")
        
        request_timestamp = datetime.utcnow().isoformat()
        logger.info(f"LLM Vision Request - Model: {model_name}, Images: {len(all_pages_images)}, Timestamp: {request_timestamp}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a PDF document analyzer with vision capabilities. Always return valid JSON. "
                        "Extract all relevant data from the document images. "
                        "CRITICAL: Only extract data that is ACTUALLY visible in the images. "
                        "Do NOT invent, guess, or create example values."
                    )
                },
                {
                    "role": "user",
                    "content": extraction_content
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        response_timestamp = datetime.utcnow().isoformat()
        usage = response.usage
        logger.info(
            f"LLM Response - Model: {model_name}, "
            f"Tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}, "
            f"Timestamp: {response_timestamp}"
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Save LLM execution results
        prompt_text = json.dumps(extraction_content, indent=2, default=str)[:1000]
        usage_dict = {
            "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(usage, 'completion_tokens', 0),
            "total_tokens": getattr(usage, 'total_tokens', 0)
        }
        _save_llm_execution_result(
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            model=model_name,
            prompt_length=len(str(extraction_content)),
            prompt_preview=prompt_text + "..." if len(prompt_text) > 1000 else prompt_text,
            response_content=content,
            usage=usage_dict
        )
        
        result = json.loads(content)
        extracted_data = result.get("extracted_data", {})
        if not isinstance(extracted_data, dict):
            logger.warning("extracted_data is not a dictionary, using empty dict")
            extracted_data = {}
        
        logger.info(f"GPT extracted {len(extracted_data)} fields")
        return extracted_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI response as JSON: {e}")
        logger.warning("Defaulting to empty data")
        return {}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        logger.warning("Defaulting to empty data")
        return {}

