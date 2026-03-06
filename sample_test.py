#!/usr/bin/env python3
import sys
import os
import random
import json
from pathlib import Path
from dataclasses import asdict

# Adjust the path to import the original processor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from steel_drawing_parser_v2 import SteelDrawingProcessor, ParsedPage

class TestProcessor(SteelDrawingProcessor):
    def parse_document_sample(self, page_limit=10):
        self.logger.info(f"Starting sample parse: {self.pdf_path.name}")
        
        # Step 1: Extract project metadata
        self.logger.info("Extracting project metadata...")
        self.extract_project_metadata()
        
        # Step 2: Extract member inventory
        self.logger.info("Extracting member inventory...")
        self.extract_member_inventory()
        
        # Step 3: Process random sample of pages
        import fitz
        doc = fitz.open(self.pdf_path)
        total_pages = len(doc)
        doc.close()
            
        sample_indices = random.sample(range(total_pages), min(page_limit, total_pages))
        sample_indices.sort()
        self.logger.info(f"Processing sample pages: {sample_indices}")
        
        for page_idx in sample_indices:
            page_content = self.process_page_with_ocr_if_needed(page_idx)
            page_type = self.classify_page(page_idx, page_content.lower())
            
            components = []
            if page_type == 'member_detail':
                components = self.extract_member_details(page_idx)
            
            sections = self.detect_section_cuts(page_idx)
            self.section_cuts.extend(sections)
            
            parsed_page = ParsedPage(
                page_index=page_idx,
                page_type=page_type,
                content=page_content,
                extracted_data={
                    'components': [asdict(comp) for comp in components if comp.evidence],
                    'section_cuts': [asdict(sec) for sec in sections if sec.evidence]
                }
            )
            self.parsed_pages.append(parsed_page)
            
        return {
            'document_info': {
                'filename': self.pdf_path.name,
                'total_pages': total_pages,
                'sample_pages': sample_indices,
                'ocr_backend_used': self.ocr_captor.backend
            },
            'project_metadata': self.project_metadata,
            'member_inventory': {k: asdict(v) for k, v in self.member_inventory.items() if v.evidence},
            'section_cuts': [asdict(sc) for sc in self.section_cuts if sc.evidence],
            'pages': [asdict(pp) for pp in self.parsed_pages]
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python sample_test.py <input_pdf> <output_jsonl>")
        sys.exit(1)
        
    input_pdf = sys.argv[1]
    output_jsonl = sys.argv[2]
    
    tp = TestProcessor(input_pdf, ocr_backend='paddle')
    results = tp.parse_document_sample(page_limit=10)
    
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'type': 'document_info', 'data': results['document_info']}) + '\n')
        f.write(json.dumps({'type': 'project_metadata', 'data': results['project_metadata']}) + '\n')
        for k, v in results['member_inventory'].items():
            f.write(json.dumps({'type': 'member_inventory', 'data': v}) + '\n')
        for p in results['pages']:
            f.write(json.dumps({'type': 'page_data', 'data': p}) + '\n')
    
    print(f"Sample test complete. Results in {output_jsonl}")
