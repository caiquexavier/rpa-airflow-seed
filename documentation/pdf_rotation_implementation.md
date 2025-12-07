# PDF Rotation Operator - Implementation Constraints and Guidelines

## Overview

The PDF Rotation Operator (`pdf_rotate_operator.py`) is responsible for automatically detecting and correcting document orientation in PNG images. The primary goal is to ensure all documents are rotated to the **same correct position**: landscape orientation with headers at the top.

## Problem Statement

Documents can be scanned or captured in various orientations:
- **0°** - Correct orientation (landscape, headers at top)
- **90°** - Rotated clockwise (portrait)
- **180°** - Upside down (inverted)
- **270°** - Rotated counterclockwise (portrait)

The challenge is to:
1. Detect the current orientation
2. Rotate to correct position
3. **Avoid inverting documents** (180° rotation is risky)
4. **Ensure all documents end up in the same position** (landscape, headers at top)

## Key Constraints

### 1. Document Requirements

All documents must end up with:
- **Landscape orientation** (width > height)
- **Headers at the top** (keywords: 'comprovante', 'entrega', 'unilever', 'transportadora', 'dados', 'nf-e')
- **Footers NOT at the top** (keywords: 'conferente', 'assinatura', 'nome', 'telefone', 'retorno', 'mercadorias')

### 2. Critical Rules

#### Never Rotate to 180° Unless Absolutely Necessary
- 180° rotations are **extremely risky** - can invert documents
- Apply **80% penalty** to 180° rotation scores
- Require **perfect conditions** (landscape + 5+ headers + 85%+ confidence) to allow 180°
- **Reject 180° from OSD** completely - don't even validate

#### Always Check Original (0°) First
- If document at 0° is already correct → return 0° immediately
- Only test other rotations if 0° is not correct
- Prefer 0° if it's landscape, even if headers aren't perfect

#### Landscape is Mandatory
- Documents **must** be landscape (width > height) after rotation
- Apply **90% penalty** to portrait orientations
- Only accept rotations that produce landscape orientation

### 3. Detection Strategy

The implementation uses a **two-phase approach**:

#### Phase 1: OSD Detection (Tesseract Orientation and Script Detection)
- Fast initial detection using Tesseract OSD
- **Reject 180°** from OSD completely
- For 90°/270°: validate that rotation produces correct orientation
- Only accept if landscape + headers at top

#### Phase 2: Best-of-Four Testing
- Test all rotations: 0°, 90°, 270°, 180°
- Score each rotation based on:
  - Orientation correctness (landscape + headers at top)
  - OCR confidence
  - Header/footer keyword positions
- Select best rotation that produces correct orientation

## Implementation Details

### `check_document_orientation()` Function

**Purpose**: Check if a document is correctly oriented.

**Returns**:
```python
{
    "is_correct": bool,      # True if landscape + headers at top + no footers at top
    "headers_at_top": int,   # Count of header keywords in first 40 words
    "footers_at_top": int,   # Count of footer keywords in first 40 words
    "headers_at_end": int,   # Count of header keywords in last 40 words
    "is_landscape": bool     # True if width > height
}
```

**Key Logic**:
- Document is correct if: `headers_at_top >= 2 AND footers_at_top == 0 AND is_landscape == True`
- Checks first 40 words for headers/footers
- Checks last 40 words to detect if headers are at end (indicates upside down)

### `detect_rotation_best_of_four()` Function

**Strategy**:
1. Check if 0° is already correct → return 0° immediately
2. Test rotations: 90°, 270°, 180° (in that order)
3. Score each rotation:
   - **Perfect score (200+ points)**: landscape + 2+ headers at top + no footers at top
   - **Partial score (50+ points)**: landscape + 1+ headers at top
   - **Low score**: portrait or incorrect orientation
4. Apply penalties:
   - **80% penalty** for 180° rotations
   - **90% penalty** for portrait orientations
5. Only accept rotation if it produces correct orientation

**Scoring Formula**:
```
score = base_score + (headers_at_top * 30) + confidence
- Apply 80% penalty if rotation == 180°
- Apply 90% penalty if not landscape
```

### `validate_rotation()` Function

**Purpose**: Final validation before applying rotation.

**Rules**:
- Always accept 0° (no rotation)
- For 180°: reject unless perfect (correct orientation + no footers at top)
- For other rotations: accept if produces correct orientation

### `detect_rotation()` Function

**Main Detection Flow**:
1. Try OSD detection first
   - If 180° detected → reject immediately
   - If 90°/270° detected → validate produces correct orientation
   - If valid → return rotation
2. Fallback to best-of-four
   - Test all rotations
   - Select best that produces correct orientation
   - Validate final selection
3. Return rotation angle

## Header and Footer Keywords

### Header Keywords (should be at TOP)
- 'comprovante'
- 'entrega'
- 'unilever'
- 'transportadora'
- 'dados'
- 'nf-e'
- 'nota'
- 'fiscal'

### Footer Keywords (should be at BOTTOM, NOT at top)
- 'conferente'
- 'assinatura'
- 'nome'
- 'telefone'
- 'retorno'
- 'mercadorias'
- 'não'
- 'entregues'

## Scoring and Penalties

### Rotation Penalties
- **180° rotation**: 80% score reduction (multiply by 0.2)
- **Portrait orientation**: 90% score reduction (multiply by 0.1)
- **Low confidence (<30%)**: 80% score reduction (multiply by 0.2)

### Score Calculation
- **Perfect orientation**: 200 points base + (headers × 30) + confidence
- **Partial orientation**: 50 points base + (headers × 10) + (confidence × 0.5)
- **Incorrect orientation**: confidence × 0.3

## Important Considerations

### 1. Performance
- OSD detection is fast but not always accurate
- Best-of-four requires 4 OCR operations (one per rotation)
- Logo detection was removed for performance reasons
- Current approach prioritizes correctness over speed

### 2. Accuracy vs Safety
- **Safety first**: Prefer 0° (no rotation) if uncertain
- **Never risk inverting**: Heavy penalties for 180°
- **Consistency**: All documents must end up in same position

### 3. Edge Cases
- Documents with little text: May not detect headers correctly
- Poor quality scans: OCR confidence may be low
- Mixed orientations: Some pages may need different rotations

### 4. Validation Requirements
- **Minimum text**: Need at least 10 words to validate
- **Header threshold**: Require 2+ header keywords at top
- **Footer check**: Even 1 footer keyword at top is suspicious
- **Landscape check**: Must verify width > height

## Testing and Validation

### Test Cases to Verify
1. ✅ Document already correct (0°) → should return 0°
2. ✅ Document rotated 90° → should rotate to 0° (270° rotation)
3. ✅ Document rotated 270° → should rotate to 0° (90° rotation)
4. ✅ Document inverted (180°) → should rotate to 0° (180° rotation) **only if perfect**
5. ✅ Document in portrait → should rotate to landscape
6. ✅ Multiple documents → all should end up in same position

### Common Issues and Solutions

#### Issue: Documents being inverted (180°)
**Solution**: 
- Reject 180° from OSD completely
- Apply 80% penalty to 180° in scoring
- Require perfect conditions to allow 180°
- Compare 180° score with 0° - prefer 0° if close

#### Issue: Documents in portrait position
**Solution**:
- Check aspect ratio (width > height)
- Apply 90% penalty to portrait orientations
- Only accept rotations that produce landscape

#### Issue: Inconsistent orientations
**Solution**:
- Always check 0° first
- Prefer 0° if it's landscape, even if not perfect
- Ensure all rotations produce same final position

## Future Improvements

### Potential Enhancements
1. **Logo detection**: Could add back if performance allows
2. **Multi-page handling**: Handle documents with mixed orientations
3. **Confidence thresholds**: Tune thresholds based on real data
4. **Machine learning**: Train model on known correct/incorrect orientations
5. **User feedback**: Allow manual correction and learn from it

### Performance Optimizations
1. Cache OCR results for same image
2. Use faster OCR modes for initial checks
3. Parallel processing for multiple images
4. Skip validation if OSD confidence is very high

## Code Structure

```
pdf_rotate_operator.py
├── check_document_orientation()      # Check if document is correctly oriented
├── detect_rotation_osd()            # Fast OSD detection
├── detect_rotation_best_of_four()   # Test all rotations and pick best
├── validate_rotation()               # Final validation
├── detect_rotation()                 # Main detection function
└── PdfRotateOperator                 # Airflow operator class
```

## References

- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- PIL/Pillow: https://pillow.readthedocs.io/
- Airflow Operators: https://airflow.apache.org/docs/apache-airflow/stable/concepts/operators.html

## Last Updated

2025-12-07 - Current implementation with landscape check and strict 180° prevention

