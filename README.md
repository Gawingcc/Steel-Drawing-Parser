# Steel Shop Drawing Parser

A Python application for extracting structured data from steel fabrication shop drawing PDFs. This tool parses steel shop drawing "books" and outputs structured JSON/JSONL data with evidence tracking.

## Features

- **Project Metadata Extraction**: Extracts project codes, client information, and drawing numbers from filenames, bookmarks, and first pages
- **Member Inventory Parsing**: Identifies and extracts member mark/section tables from early pages
- **Page Classification**: Classifies pages as cover, inventory, plan, detail, or section views
- **Component Extraction**: Detects and extracts bolts, plates, angles, stiffeners, and welds from detail pages
- **Section Cut Detection**: Finds and links section cuts (A-A, B-B) across pages
- **Evidence Tracking**: Records page number, bounding box coordinates, and source text for every extracted field
- **High Accuracy**: Built with accuracy as the top priority

## Requirements

- Python 3.8+
- PyMuPDF (fitz)
- pandas
- numpy
- opencv-python
- Pillow
- pytesseract
- pdf2image

## Installation

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Install system dependencies for OCR (Ubuntu/Debian):
   ```bash
   sudo apt-get install tesseract-ocr libtesseract-dev poppler-utils
   ```

## Usage

### Command Line

```bash
python steel_drawing_parser.py <input_pdf_path> <output_json_path>
```

Example:
```bash
python steel_drawing_parser.py ./drawings/steel_framing.pdf ./output/steel_data.json
```

### Programmatic Usage

```python
from steel_drawing_parser import SteelDrawingParser

# Create parser instance
parser = SteelDrawingParser("./drawings/steel_framing.pdf")

# Parse the document
results = parser.parse_document()

# Export results
parser.export_results("./output/steel_data.json")

# Or export as JSONL
parser.export_results("./output/steel_data.jsonl", format='jsonl')
```

## Output Format

The parser generates a structured JSON file with the following sections:

```json
{
  "document_info": {
    "filename": "steel_framing.pdf",
    "total_pages": 15,
    "parsed_date": "2026-02-07T01:21:04.123456"
  },
  "project_metadata": {
    "project_codes": ["ABC-123"],
    "project_name": "Sample Project",
    "client": "Sample Client",
    "drawing_number": "DRW-001"
  },
  "member_inventory": {
    "W12x50": {
      "mark_id": "W12x50",
      "section": "W12x50",
      "length": "15'-6\"",
      "weight": "50 lbs/ft",
      "evidence": {
        "page_number": 1,
        "bbox": [100, 200, 300, 250],
        "source_text": "W12x50 - 15'-6\""
      }
    }
  },
  "section_cuts": [
    {
      "name": "A-A",
      "page_number": 5,
      "bbox": [150, 300, 180, 320],
      "evidence": {
        "page_number": 5,
        "bbox": [150, 300, 180, 320],
        "source_text": "A-A"
      }
    }
  ],
  "pages": [
    {
      "page_number": 0,
      "page_type": "cover",
      "content": "Full text content of page...",
      "extracted_data": {
        "components": [],
        "section_cuts": []
      }
    }
  ]
}
```

## How It Works

1. **Metadata Extraction**: Parses filename, bookmarks, and first few pages to extract project information
2. **Inventory Identification**: Scans early pages for tables containing member marks and sections
3. **Page Classification**: Uses keyword analysis to classify each page type
4. **Detail Analysis**: On detail pages, identifies components like bolts, plates, angles, etc.
5. **Section Cut Detection**: Finds standard notation for section cuts (A-A, B-B, etc.)
6. **Evidence Tracking**: Maintains bounding box coordinates and source text for verification

## Accuracy Considerations

- The parser uses multiple detection methods to ensure accuracy
- All extracted data includes evidence (coordinates, page number, source text)
- OCR is used for text extraction when needed
- Table detection algorithms identify structured data

## Customization

You can extend the parser by:
- Adding new component types to the `Component` class
- Modifying regex patterns for specific company standards
- Adjusting page classification keywords
- Adding custom validation rules

## Troubleshooting

- If table detection fails, ensure the PDF has clean, structured tables
- For poor OCR results, try preprocessing the PDF to improve text quality
- Check that all required dependencies are installed correctly