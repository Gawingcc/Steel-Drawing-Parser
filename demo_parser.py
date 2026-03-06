#!/usr/bin/env python3
"""
Demo script for the Steel Drawing Parser
Shows how to use the parser with sample data
"""

import json
import os
from pathlib import Path
from steel_drawing_parser import SteelDrawingParser


def create_sample_pdf_description():
    """
    Creates a sample description of what a typical steel shop drawing PDF looks like
    This would normally be replaced with actual PDF processing
    """
    sample_structure = {
        "description": "Sample steel shop drawing book structure",
        "typical_pages": [
            {
                "page": 0,
                "type": "cover",
                "content": "Title sheet with project information"
            },
            {
                "page": 1,
                "type": "inventory",
                "content": "Member mark list with sections and quantities"
            },
            {
                "page": 2,
                "type": "plan",
                "content": "General arrangement plans"
            },
            {
                "page": 3,
                "type": "detail",
                "content": "Detailed member connections with components"
            }
        ],
        "expected_outputs": {
            "project_metadata": ["project_code", "client", "drawing_numbers"],
            "member_inventory": ["mark_id", "section", "length", "weight"],
            "components": ["bolts", "plates", "angles", "stiffeners", "welds"],
            "section_cuts": ["A-A", "B-B", "C-C"]
        }
    }
    
    return sample_structure


def demo_usage():
    """Demonstrate how to use the parser"""
    print("Steel Drawing Parser Demo")
    print("=" * 50)
    
    # Show sample structure
    sample_desc = create_sample_pdf_description()
    print("\nTypical Steel Shop Drawing Structure:")
    for page_info in sample_desc["typical_pages"]:
        print(f"  Page {page_info['page']}: {page_info['type']} - {page_info['content']}")
    
    print(f"\nExpected Outputs:")
    for category, items in sample_desc["expected_outputs"].items():
        print(f"  {category}: {', '.join(items)}")
    
    print("\n" + "=" * 50)
    print("To use the parser with a real PDF:")
    print("python steel_drawing_parser.py <input_pdf_path> <output_json_path>")
    
    # Show example usage with a hypothetical PDF
    print("\nExample:")
    print("python steel_drawing_parser.py ./shop_drawings/steel_framing.pdf ./output/steel_data.json")
    
    # Show what the output structure would look like
    print("\nOutput JSON structure will contain:")
    print("- Document info (filename, page count)")
    print("- Project metadata (codes, client, etc.)")
    print("- Member inventory (mark IDs linked to sections)")
    print("- Page-by-page analysis with classifications")
    print("- Components extracted from detail pages")
    print("- Section cuts detected across pages")
    print("- Evidence tracking (page numbers, coordinates, source text)")


def create_example_usage_script():
    """Create an example script showing how to integrate the parser programmatically"""
    
    example_script = '''
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
'''
    
    with open('example_usage.py', 'w') as f:
        f.write(example_script)
    
    print("\nCreated example_usage.py with programmatic integration example")


if __name__ == "__main__":
    demo_usage()
    create_example_usage_script()
    print("\nDemo complete! Created example_usage.py for integration examples.")