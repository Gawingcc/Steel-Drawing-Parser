#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path
from dataclasses import asdict

# Adjust the path to import the original processor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from steel_drawing_parser_v2 import SteelDrawingProcessor, ParsedPage

class InventoryProcessor(SteelDrawingProcessor):
    def parse_inventory_pages(self, pages=[2, 3, 4]):
        self.logger.info(f"Targeted inventory parse on pages: {pages}")
        self.extract_project_metadata()
        
        # Override to specifically target pages for inventory
        import fitz
        doc = fitz.open(self.pdf_path)
        
        for page_idx in pages:
            if page_idx >= len(doc): continue
            page_content = self.process_page_with_ocr_if_needed(page_idx)
            # The base class extract_member_inventory handles the logic but we need to feed it the right pages
            # For this MVP, we rely on the base logic's find_tables()
            
        doc.close()
        self.extract_member_inventory() # Base class logic will scan first 5 pages anyway
            
        return {
            'document_info': {'filename': self.pdf_path.name, 'ocr_backend_used': self.ocr_captor.backend},
            'project_metadata': self.project_metadata,
            'member_inventory': {k: asdict(v) for k, v in self.member_inventory.items() if v.evidence}
        }

if __name__ == "__main__":
    input_pdf = "projects/steel-drawing-parser/ingest/051200-0016-0 - Shop Drawings for Level 2 Steel (SEQ 104 & 105) (SMS-021)_LeM.pdf"
    output_jsonl = "projects/steel-drawing-parser/output/inventory_truth.jsonl"
    
    tp = InventoryProcessor(input_pdf, ocr_backend='paddle')
    results = tp.parse_inventory_pages([2, 3, 4])
    
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'type': 'inventory_summary', 'data': results}) + '\n')
    
    print(f"Inventory test complete. Found {len(results['member_inventory'])} items.")
