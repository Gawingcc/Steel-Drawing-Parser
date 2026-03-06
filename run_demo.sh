#!/bin/bash

echo "Steel Shop Drawing Parser - Demo"
echo "================================"

echo "Step 1: Checking dependencies..."
python3 -c "import fitz, pandas, numpy, cv2, PIL, pytesseract, pdf2image" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ All dependencies are available"
else
    echo "! Some dependencies may be missing, attempting to install with --break-system-packages..."
    pip install --break-system-packages -r requirements.txt
fi

echo
echo "Step 2: Creating a sample output directory..."
mkdir -p output

echo
echo "Step 3: Running the demo script..."
python3 demo_parser.py

echo
echo "Step 4: Verifying the parser module..."
python3 -c "
from steel_drawing_parser import SteelDrawingParser
print('✓ Parser module successfully imported')
print('✓ Ready to process steel shop drawing PDFs')
"

echo
echo "Step 5: Showing the main parser code structure..."
head -50 steel_drawing_parser.py

echo
echo "To use the parser with a real PDF:"
echo "python3 steel_drawing_parser.py <input_pdf_path> <output_json_path>"
echo
echo "Example:"
echo "python3 steel_drawing_parser.py ./sample_drawings/steel_framing.pdf ./output/steel_data.json"