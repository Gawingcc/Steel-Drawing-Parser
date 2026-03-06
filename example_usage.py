
#!/usr/bin/env python3
"""
Example of how to use the Steel Drawing Parser in your own code
"""

from steel_drawing_parser import SteelDrawingParser
import json

def process_steel_drawings(pdf_path, output_path):
    """
    Process a steel drawing PDF and save structured output
    """
    # Create parser instance
    parser = SteelDrawingParser(pdf_path)
    
    # Parse the document
    results = parser.parse_document()
    
    # Export results
    parser.export_results(output_path)
    
    # Print summary
    print(f"Processed {results['document_info']['total_pages']} pages")
    print(f"Found {len(results['member_inventory'])} members in inventory")
    print(f"Detected {len(results['section_cuts'])} section cuts")
    
    return results

# Example usage
if __name__ == "__main__":
    # Replace with your actual PDF path
    input_pdf = "./your_steel_drawing.pdf"
    output_json = "./output/structured_data.json"
    
    if os.path.exists(input_pdf):
        results = process_steel_drawings(input_pdf, output_json)
        print("Processing complete!")
    else:
        print(f"PDF file {input_pdf} not found")
