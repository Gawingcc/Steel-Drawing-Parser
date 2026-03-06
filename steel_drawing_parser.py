#!/usr/bin/env python3
"""
Steel Shop Drawing Parser
Extracts structured data from steel fabrication drawings
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
import cv2
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import re


@dataclass
class Evidence:
    """Evidence for extracted data including source information"""
    page_number: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    source_text: str
    confidence: float = 1.0


@dataclass
class MemberMark:
    """Information about a structural member"""
    mark_id: str
    section: str
    length: Optional[str] = None
    weight: Optional[str] = None
    material: Optional[str] = None
    evidence: Optional[Evidence] = None


@dataclass
class Component:
    """Component of a structural member (plate, bolt, etc.)"""
    component_type: str  # 'plate', 'bolt', 'angle', 'stiffener', 'weld'
    description: str
    dimensions: Optional[str] = None
    quantity: Optional[int] = None
    material: Optional[str] = None
    evidence: Optional[Evidence] = None


@dataclass
class SectionCut:
    """Section cut reference (A-A, B-B, etc.)"""
    name: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    evidence: Optional[Evidence] = None


@dataclass
class ParsedPage:
    """Classification and content of a parsed page"""
    page_number: int
    page_type: str  # 'cover', 'inventory', 'plan', 'detail', 'section'
    content: str
    extracted_data: Dict[str, Any]


class SteelDrawingParser:
    """Main parser class for steel shop drawings"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)
        self.project_metadata = {}
        self.member_inventory = {}  # mark_id -> MemberMark
        self.section_cuts = []  # List of SectionCut objects
        self.parsed_pages = []  # List of ParsedPage objects
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def extract_project_metadata(self) -> Dict[str, Any]:
        """Extract project metadata from filename, bookmarks, and first pages"""
        metadata = {}
        
        # Extract from filename
        filename = self.pdf_path.stem
        # Common patterns in steel drawing filenames
        patterns = [
            r'([A-Z0-9]+-[A-Z0-9]+)',  # Project code like ABC-123
            r'(\d{4}-\d{2}-\d{2})',    # Date
            r'([A-Z]{2,4}-\d+)',       # Drawing series
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, filename)
            if matches:
                metadata['project_codes'] = matches
                
        # Extract from first few pages
        for page_num in range(min(3, len(self.doc))):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Look for common metadata fields
            project_match = re.search(r'Project:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if project_match:
                metadata['project_name'] = project_match.group(1).strip()
                
            client_match = re.search(r'Client:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if client_match:
                metadata['client'] = client_match.group(1).strip()
                
            drawing_match = re.search(r'Drawing\s*#?:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if drawing_match:
                metadata['drawing_number'] = drawing_match.group(1).strip()
        
        # Extract bookmarks if available
        try:
            toc = self.doc.get_toc()
            if toc:
                metadata['bookmarks'] = [item[1] for item in toc]
        except:
            pass
            
        self.project_metadata = metadata
        return metadata
    
    def extract_member_inventory(self) -> Dict[str, MemberMark]:
        """Extract member mark/section list tables from early pages"""
        inventory = {}
        
        # Check first 5 pages for inventory tables
        for page_num in range(min(5, len(self.doc))):
            page = self.doc[page_num]
            # Look for table-like structures
            tables = page.find_tables()
            
            for table in tables:
                try:
                    df = table.to_pandas()
                    # Look for columns that might contain member marks
                    potential_mark_cols = []
                    potential_section_cols = []
                    
                    for col_idx, col_name in enumerate(df.columns):
                        col_str = str(col_name).lower()
                        if any(keyword in col_str for keyword in ['mark', 'piece', 'member', 'tag']):
                            potential_mark_cols.append(col_idx)
                        elif any(keyword in col_str for keyword in ['section', 'size', 'shape', 'spec']):
                            potential_section_cols.append(col_idx)
                    
                    # If we found likely mark and section columns, process the table
                    if potential_mark_cols and potential_section_cols:
                        for _, row in df.iterrows():
                            mark_val = None
                            section_val = None
                            
                            # Extract mark
                            for col_idx in potential_mark_cols:
                                val = str(row.iloc[col_idx]).strip()
                                if val and not pd.isna(val) and val != '':
                                    mark_val = val
                                    break
                                    
                            # Extract section
                            for col_idx in potential_section_cols:
                                val = str(row.iloc[col_idx]).strip()
                                if val and not pd.isna(val) and val != '':
                                    section_val = val
                                    break
                            
                            if mark_val and section_val:
                                evidence_bbox = (table.bbox.x0, table.bbox.y0, table.bbox.x1, table.bbox.y1)
                                evidence = Evidence(
                                    page_number=page_num,
                                    bbox=evidence_bbox,
                                    source_text=f"{mark_val} - {section_val}"
                                )
                                
                                member = MemberMark(
                                    mark_id=mark_val,
                                    section=section_val,
                                    evidence=evidence
                                )
                                inventory[mark_val] = member
                                
                except Exception as e:
                    self.logger.warning(f"Could not parse table on page {page_num}: {e}")
        
        self.member_inventory = inventory
        return inventory
    
    def classify_page(self, page_num: int) -> str:
        """Classify page type based on content and structure"""
        page = self.doc[page_num]
        text = page.get_text().lower()
        
        # Keywords for different page types
        cover_keywords = ['title', 'sheet', 'drawing', 'project', 'revision', 'date']
        inventory_keywords = ['mark', 'piece', 'member', 'list', 'summary', 'quantity']
        plan_keywords = ['plan', 'elevation', 'layout', 'assembly', 'general']
        detail_keywords = ['detail', 'detailing', 'connection', 'joint', 'fabrication']
        section_keywords = ['section', 'cut', 'view', 'detail']
        
        # Count occurrences of keywords
        cover_score = sum(1 for kw in cover_keywords if kw in text)
        inventory_score = sum(1 for kw in inventory_keywords if kw in text)
        plan_score = sum(1 for kw in plan_keywords if kw in text)
        detail_score = sum(1 for kw in detail_keywords if kw in text)
        section_score = sum(1 for kw in section_keywords if kw in text)
        
        scores = {
            'cover': cover_score,
            'inventory': inventory_score,
            'plan': plan_score,
            'detail': detail_score,
            'section': section_score
        }
        
        # Return the highest scoring classification
        return max(scores, key=scores.get)
    
    def extract_member_details(self, page_num: int) -> List[Component]:
        """Extract components from member detail pages"""
        components = []
        page = self.doc[page_num]
        text = page.get_text()
        
        # Patterns for different component types
        patterns = {
            'bolt': [
                r'(\d+)\s*x?\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+BOLT',
                r'BOLT\s+(\d+)\s+x\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
            ],
            'plate': [
                r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+PLATE',
                r'PLATE\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
            ],
            'angle': [
                r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+ANGLE',
                r'ANGLE\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
            ],
            'stiffener': [
                r'STIFFENER',
                r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+STIFF',
            ],
            'weld': [
                r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+WELD',
                r'WELD\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
            ]
        }
        
        for comp_type, comp_patterns in patterns.items():
            for pattern in comp_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        desc = ' x '.join([str(x) for x in match if x])
                    else:
                        desc = str(match)
                        
                    # Find the bounding box for this match
                    text_instances = page.search_for(str(desc))
                    if text_instances:
                        bbox = text_instances[0]  # Take first occurrence
                        evidence = Evidence(
                            page_number=page_num,
                            bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                            source_text=desc
                        )
                    else:
                        evidence = None
                    
                    component = Component(
                        component_type=comp_type,
                        description=desc,
                        evidence=evidence
                    )
                    components.append(component)
        
        return components
    
    def detect_section_cuts(self, page_num: int) -> List[SectionCut]:
        """Detect section cuts (A-A, B-B, etc.) on a page"""
        section_cuts = []
        page = self.doc[page_num]
        text = page.get_text()
        
        # Pattern for section cuts like A-A, B-B, etc.
        pattern = r'\b([A-Z])-([A-Z])\b|\b([A-Z])-([A-Z])\b'
        matches = re.findall(pattern, text)
        
        for match in matches:
            # Handle both tuple formats from regex
            letters = [m for m in match if m != '']
            if len(letters) >= 2:
                name = f"{letters[0]}-{letters[1]}"
                
                # Find the position of this section cut in the text
                search_text = name
                text_instances = page.search_for(search_text)
                
                for inst in text_instances:
                    evidence = Evidence(
                        page_number=page_num,
                        bbox=(inst.x0, inst.y0, inst.x1, inst.y1),
                        source_text=name
                    )
                    
                    section_cut = SectionCut(
                        name=name,
                        page_number=page_num,
                        bbox=(inst.x0, inst.y0, inst.x1, inst.y1),
                        evidence=evidence
                    )
                    section_cuts.append(section_cut)
        
        return section_cuts
    
    def parse_document(self) -> Dict[str, Any]:
        """Main parsing method that orchestrates the entire process"""
        self.logger.info(f"Starting to parse: {self.pdf_path.name}")
        
        # Step 1: Extract project metadata
        self.logger.info("Extracting project metadata...")
        self.extract_project_metadata()
        
        # Step 2: Extract member inventory
        self.logger.info("Extracting member inventory...")
        self.extract_member_inventory()
        
        # Step 3: Process each page
        self.logger.info("Processing individual pages...")
        for page_num in range(len(self.doc)):
            page_type = self.classify_page(page_num)
            
            # Extract additional data based on page type
            components = []
            sections = []
            
            if page_type == 'detail':
                components = self.extract_member_details(page_num)
            
            sections = self.detect_section_cuts(page_num)
            self.section_cuts.extend(sections)
            
            # Store parsed page
            page = self.doc[page_num]
            content = page.get_text()
            parsed_page = ParsedPage(
                page_number=page_num,
                page_type=page_type,
                content=content,
                extracted_data={
                    'components': [asdict(comp) for comp in components],
                    'section_cuts': [asdict(sec) for sec in sections]
                }
            )
            self.parsed_pages.append(parsed_page)
        
        # Step 4: Compile final results
        result = {
            'document_info': {
                'filename': self.pdf_path.name,
                'total_pages': len(self.doc),
                'parsed_date': pd.Timestamp.now().isoformat()
            },
            'project_metadata': self.project_metadata,
            'member_inventory': {k: asdict(v) for k, v in self.member_inventory.items()},
            'section_cuts': [asdict(sc) for sc in self.section_cuts],
            'pages': [asdict(pp) for pp in self.parsed_pages]
        }
        
        self.logger.info("Parsing complete!")
        return result
    
    def export_results(self, output_path: str, format: str = 'json'):
        """Export results to JSON or JSONL"""
        results = self.parse_document()
        
        if format.lower() == 'jsonl':
            with open(output_path, 'w') as f:
                for page_data in results['pages']:
                    f.write(json.dumps(page_data) + '\n')
        else:  # JSON
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Results exported to {output_path}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python steel_drawing_parser.py <input_pdf_path> <output_json_path>")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_json = sys.argv[2]
    
    if not os.path.exists(input_pdf):
        print(f"Error: Input file {input_pdf} does not exist")
        sys.exit(1)
    
    parser = SteelDrawingParser(input_pdf)
    parser.export_results(output_json)


if __name__ == "__main__":
    main()