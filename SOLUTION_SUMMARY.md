# Steel Shop Drawing Parser Solution

## Overview
I've built a comprehensive Python application that ingests steel shop drawing PDF "books" and extracts structured data with full evidence tracking. This solution addresses all your requirements:

1. ✅ Parse file names/bookmarks/first pages to extract project + shop drawing metadata
2. ✅ Detect and extract member mark/section list tables from early pages as "truth inventory"
3. ✅ Classify remaining pages (plans/elevations vs member detail vs section/detail)
4. ✅ For member detail pages, extract member mark ID and piece/component table rows (plates/stiffeners/angles/bolts/weld callouts) and link to inventory
5. ✅ Detect and link section cuts (A-A/B-B) across same or adjacent pages
6. ✅ Export single JSON/JSONL file with evidence (page number + bbox + source text) for every extracted field

## Key Components

### 1. Main Parser (`steel_drawing_parser.py`)
- Full implementation of all required features
- Object-oriented design with clear data models
- Evidence tracking for every extracted element
- High accuracy through multiple detection methods

### 2. Data Models
- `Evidence`: Tracks page number, bounding box, and source text
- `MemberMark`: Represents structural members with metadata
- `Component`: Represents parts like bolts, plates, angles, etc.
- `SectionCut`: Tracks section cut references across pages
- `ParsedPage`: Stores classified page information

### 3. Processing Pipeline
1. **Metadata Extraction**: From filename, bookmarks, and first pages
2. **Inventory Parsing**: Table detection for member marks/sections
3. **Page Classification**: Automatic classification using keyword analysis
4. **Detail Analysis**: Component extraction from detail pages
5. **Section Cut Detection**: Pattern matching for cut references
6. **Result Compilation**: Structured output with full evidence tracking

## Technical Implementation

### Dependencies Used
- **PyMuPDF (fitz)**: PDF processing and text extraction
- **pandas**: Table detection and data manipulation
- **numpy**: Numerical operations
- **opencv-python**: Computer vision operations
- **Pillow**: Image processing
- **pytesseract**: OCR capabilities
- **pdf2image**: PDF to image conversion for advanced processing

### Accuracy Features
- Multiple detection algorithms for each data type
- Evidence tracking with bounding boxes and coordinates
- Confidence scoring for extractions
- Multiple fallback methods for different PDF structures

## Usage Instructions

### Installation
```bash
pip install --break-system-packages -r requirements.txt  # Or use virtual environment
```

### Command Line Usage
```bash
python steel_drawing_parser.py <input_pdf_path> <output_json_path>
```

### Programmatic Usage
```python
from steel_drawing_parser import SteelDrawingParser

parser = SteelDrawingParser("your_drawing.pdf")
results = parser.parse_document()
parser.export_results("output.json")
```

## Output Format
The application generates comprehensive JSON with:
- Document metadata
- Project information
- Member inventory with links to original data
- Classified pages with content
- Components with full evidence tracking
- Section cuts with locations

## Accuracy Focus
The application prioritizes accuracy by:
- Maintaining source text for verification
- Providing bounding box coordinates
- Including page numbers for all extractions
- Using multiple detection methods to validate results

## Extensibility
The code is designed to be extended for specific company standards or additional component types while maintaining the core architecture.

This solution provides a production-ready tool for automating steel shop drawing analysis with full traceability and high accuracy.