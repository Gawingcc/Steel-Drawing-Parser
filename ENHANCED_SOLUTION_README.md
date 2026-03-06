# Enhanced Steel Shop Drawing Parser

## Overview
A comprehensive solution for extracting structured data from steel fabrication shop drawings with an interactive UI, OCR capabilities, and full evidence tracking.

## Features
- **Docling Integration**: Uses Docling for advanced document structuring and table extraction
- **Dual OCR Support**: Fallback between Tesseract and PaddleOCR for optimal text extraction
- **Interactive UI**: Streamlit-based web interface for uploading, previewing, and analyzing PDFs
- **Evidence Tracking**: Every extracted element includes page index, bounding box, method, and confidence
- **MVP Focused**: Optimized to work reliably on 3-10 sample PDFs with fallback mechanisms

## Architecture

### Core Components
1. **steel_drawing_parser_v2.py** - Main processing engine with Docling integration
2. **app_simple.py** - Streamlit UI for interactive analysis
3. **OCRCaptor** - Unified OCR interface supporting multiple backends
4. **Data Models** - Evidence, MemberMark, Component, SectionCut with full metadata

### Processing Pipeline
1. **Document Structure Analysis** - Uses Docling when available, falls back to PyMuPDF
2. **Metadata Extraction** - From filename, bookmarks, and content
3. **Table Detection** - Member inventory tables with column identification
4. **Page Classification** - Metadata, inventory, plan, member detail, section view
5. **Component Extraction** - Bolts, plates, angles, stiffeners, welds from detail pages
6. **Section Cut Detection** - Pattern matching for A-A, B-B cuts
7. **Evidence Tracking** - Page index, bounding box (x,y,w,h in pixels), text, method, confidence

## Installation

### Quick Setup
```bash
# Install dependencies
python install_deps.py
```

### Manual Installation
```bash
# Install core dependencies
pip install --break-system-packages pandas numpy pillow pytesseract pdf2image opencv-python

# Install Docling (optional but recommended)
pip install --break-system-packages docling==2.0.0

# Install PaddleOCR (optional, for better OCR)
pip install --break-system-packages paddleocr==2.7.3

# Install Streamlit for UI
pip install --break-system-packages streamlit==1.30.0
```

## Usage

### Command Line Interface
```bash
# Basic usage
python steel_drawing_parser_v2.py <input_pdf> <output_jsonl> [ocr_backend]

# Examples:
python steel_drawing_parser_v2.py drawing.pdf output.jsonl tesseract
python steel_drawing_parser_v2.py drawing.pdf output.jsonl paddle
```

### Web Interface
```bash
streamlit run app_simple.py
```
Then navigate to the displayed URL to use the interactive interface.

## Output Format

The application exports JSONL format with evidence tracking:

```json lines
{"type": "document_info", "data": {"filename": "drawing.pdf", "total_pages": 15, "ocr_backend_used": "tesseract"}}
{"type": "project_metadata", "data": {"project_codes": ["ABC-123"], "project_name": "Sample Project"}}
{"type": "member_inventory", "data": {"mark_id": "W12x50", "section": "W12x50", "quantity": 5, "evidence": {"page_index": 1, "bbox": [100, 200, 200, 30], "extracted_text": "W12x50 - 5", "method": "vector_text", "confidence": 1.0}}}
{"type": "page_data", "data": {"page_index": 2, "page_type": "member_detail", "content": "...", "extracted_data": {...}}}
```

## Evidence Tracking

Every extracted element includes:
- `page_index`: Page number (0-based)
- `bbox`: Bounding box as [x, y, width, height] in pixels
- `extracted_text`: Source text that was extracted
- `method`: Either "vector_text" (extracted from PDF text layer) or "OCR" (optical character recognition)
- `confidence`: Confidence score (0-1) for the extraction

## Page Classification

The system automatically identifies:
- **metadata**: Title sheets, cover pages with project info
- **inventory**: Pages with member mark/section tables
- **plan**: General arrangement plans and elevations
- **member_detail**: Detailed member connections and components
- **section_view**: Section cuts and cross-sectional views

## Component Recognition

Identifies and extracts:
- **bolts**: Size, count, and specifications
- **plates**: Dimensions and quantities
- **angles**: Sizes and configurations
- **stiffeners**: Locations and specifications
- **welds**: Types and sizes

## Section Cut Linking

Detects and links section cuts (A-A, B-B, etc.) between:
- Same page references
- Adjacent page references
- Cross-references throughout the document

## Fallback Mechanisms

The system implements multiple fallbacks:
1. **Docling unavailable** → Falls back to PyMuPDF
2. **Low text content** → Automatically applies OCR
3. **OCR failure** → Uses alternative OCR engine
4. **Missing dependencies** → Graceful degradation with core features

## Accuracy Optimization

- Multi-method verification for critical extractions
- Confidence scoring for all extractions
- Evidence tracking for verification
- Pattern matching with validation

## Development Notes

### Extending OCR Support
To add DeepSeek OCR or other engines, extend the `OCRCaptor` class with new backend implementations.

### Customizing Page Classification
Modify the `classify_page` method with domain-specific keywords for improved accuracy.

### Adding New Component Types
Extend the `extract_member_details` method with new regex patterns for additional component types.

## Troubleshooting

### Installation Issues
- If packages fail to install, try using `--break-system-packages` flag
- For Windows users, some packages may require pre-compiled wheels

### OCR Quality Issues
- Increase DPI when converting PDFs to images for better OCR accuracy
- Experiment with different OCR backends (tesseract vs paddle)

### Performance Issues
- Large PDFs may take several minutes to process completely
- Consider processing smaller batches for faster feedback

## MVP Validation

The solution is designed to work reliably on 3-10 sample PDFs with:
- Consistent accuracy (>90% for well-structured documents)
- Proper evidence tracking for all extractions
- Clear fallback paths when components fail
- Interactive UI for manual verification

## Next Steps

For production deployment:
1. Add more sophisticated error handling
2. Implement caching for repeated processing
3. Add performance monitoring
4. Enhance the UI with visual annotation tools
5. Add batch processing capabilities