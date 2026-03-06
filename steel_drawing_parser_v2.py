#!/usr/bin/env python3
"""
Enhanced Steel Shop Drawing Parser
Uses Docling for document structuring and includes OCR capabilities
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from PIL import Image
import cv2
import pytesseract
import tempfile
import re
from pdf2image import convert_from_path

# Import PaddleOCR conditionally
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None


@dataclass
class Evidence:
    """Evidence for extracted data including source information"""
    page_index: int
    bbox: Tuple[float, float, float, float]  # x, y, width, height in pixels
    extracted_text: str
    method: str  # 'vector_text' or 'OCR'
    confidence: float = 1.0


@dataclass
class MemberMark:
    """Information about a structural member"""
    mark_id: str
    section: str
    quantity: Optional[int] = None
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
    page_index: int
    bbox: Tuple[float, float, float, float]
    evidence: Optional[Evidence] = None


@dataclass
class ParsedPage:
    """Classification and content of a parsed page"""
    page_index: int
    page_type: str  # 'metadata', 'inventory', 'plan', 'member_detail', 'section_view'
    content: str
    extracted_data: Dict[str, Any]


class OCRCaptor:
    """Unified OCR interface supporting multiple backends"""
    
    def __init__(self, backend: str = 'tesseract'):
        self.backend = backend
        self.paddle_ocr = None
        
        if backend == 'paddle':
            if PADDLEOCR_AVAILABLE:
                try:
                    self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en')
                except Exception as e:
                    logging.warning(f"PaddleOCR initialization failed: {e}. Falling back to Tesseract.")
                    self.backend = 'tesseract'
            else:
                logging.warning("PaddleOCR not available. Falling back to Tesseract.")
                self.backend = 'tesseract'
    
    def ocr_image(self, image: Image.Image) -> Tuple[str, float]:
        """
        Perform OCR on an image and return text and confidence
        """
        if self.backend == 'paddle' and self.paddle_ocr:
            # Convert PIL image to array for PaddleOCR
            img_array = np.array(image)
            if len(img_array.shape) == 2:  # Grayscale
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            result = self.paddle_ocr.ocr(img_array, cls=True)
            
            text_parts = []
            confidences = []
            
            for res in result:
                if res is not None:
                    for line in res:
                        if line is not None:
                            for item in line:
                                if isinstance(item, list) and len(item) == 2 and isinstance(item[1], tuple):
                                    text, conf = item[1]
                                    text_parts.append(text)
                                    confidences.append(conf)
                                elif len(item) == 2:
                                    text, conf = item
                                    text_parts.append(text)
                                    confidences.append(conf)
            
            full_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            return full_text, avg_confidence
        
        else:  # Tesseract
            # Convert image to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Use pytesseract to get data including confidence
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            text_parts = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                conf = int(data['conf'][i])
                if conf > 0 and text.strip():  # Only consider confident text
                    text_parts.append(text.strip())
                    confidences.append(conf)
            
            full_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            return full_text, avg_confidence / 100.0  # Normalize confidence to 0-1


class SteelDrawingProcessor:
    """Main processor class using Docling for document structuring"""
    
    def __init__(self, pdf_path: str, ocr_backend: str = 'tesseract'):
        self.pdf_path = Path(pdf_path)
        self.ocr_captor = OCRCaptor(backend=ocr_backend)
        self.project_metadata = {}
        self.member_inventory = {}  # mark_id -> MemberMark
        self.section_cuts = []  # List of SectionCut objects
        self.parsed_pages = []  # List of ParsedPage objects
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Import Docling here to handle installation issues gracefully
        try:
            from docling.datamodel.pipeline import create_pipeline
            from docling.datamodel.document import DocumentConversionInput
            from docling.document_converter import DocumentConverter
            self.docling_available = True
            self.document_converter = DocumentConverter()
        except ImportError:
            self.logger.warning("Docling not available, falling back to basic PDF processing")
            self.docling_available = False
    
    def extract_with_docling(self) -> Optional[Dict]:
        """Extract document structure using Docling if available"""
        if not self.docling_available:
            return None
        
        try:
            from docling.datamodel.document import ConversionStatus
            from docling.document_converter import FormatSupport
            from docling.datamodel.base_models import PipelineOptions, TableFormerMode, PictureFormerMode
            
            # Configure pipeline options
            pipeline_options = PipelineOptions(
                do_table_structures=True,
                table_formation_mode=TableFormerMode.BOUNDING_BOX,
                do_ocr=True,
                ocr_options=None
            )
            
            converter = DocumentConverter(
                format_support={FormatSupport.PDF},
                pipeline_options=pipeline_options
            )
            
            input_doc = DocumentConversionInput.from_paths([self.pdf_path])
            artifacts = converter.convert(input_doc)
            
            # Process results
            for art in artifacts:
                if art.status == ConversionStatus.SUCCESS:
                    doc = art.document
                    # Extract text, tables, and figures
                    text_elements = []
                    tables = []
                    
                    for item in doc.pages:
                        for element in item.elements:
                            if element.category == "Text":
                                text_elements.append(element.text)
                            elif element.category == "Table":
                                tables.append(element.export_to_dataframe())
                    
                    return {
                        'text_elements': text_elements,
                        'tables': tables,
                        'structure': doc
                    }
        
        except Exception as e:
            self.logger.warning(f"Docling extraction failed: {e}")
            return None
    
    def extract_project_metadata(self) -> Dict[str, Any]:
        """Extract project metadata from filename and first pages"""
        metadata = {}
        
        # Extract from filename
        filename = self.pdf_path.stem
        import re
        patterns = [
            r'([A-Z0-9]+-[A-Z0-9]+)',  # Project code like ABC-123
            r'([A-Z]{2,4}-\d+)',       # Drawing series
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, filename)
            if matches:
                metadata['project_codes'] = matches
                break
        
        # Use Docling if available, otherwise fall back to PyPDF2 or basic processing
        docling_result = self.extract_with_docling()
        
        if docling_result:
            # Extract from Docling results
            text_elements = docling_result.get('text_elements', [])
            combined_text = ' '.join(text_elements[:5])  # First few text elements
            
            # Look for common metadata fields
            project_match = re.search(r'Project:\s*(.+?)(?:\n|$)', combined_text, re.IGNORECASE)
            if project_match:
                metadata['project_name'] = project_match.group(1).strip()
                
            client_match = re.search(r'Client:\s*(.+?)(?:\n|$)', combined_text, re.IGNORECASE)
            if client_match:
                metadata['client'] = client_match.group(1).strip()
                
            drawing_match = re.search(r'Drawing\s*#?:\s*(.+?)(?:\n|$)', combined_text, re.IGNORECASE)
            if drawing_match:
                metadata['drawing_number'] = drawing_match.group(1).strip()
        else:
            # Fallback to basic PDF processing
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(self.pdf_path)
                
                # Check first 3 pages for metadata
                for page_num in range(min(3, len(doc))):
                    page = doc[page_num]
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
                        
                    if metadata.get('project_name') or metadata.get('client') or metadata.get('drawing_number'):
                        break  # Found some metadata, exit early
                
                doc.close()
            except ImportError:
                self.logger.warning("PyMuPDF not available for fallback processing")
        
        self.project_metadata = metadata
        return metadata
    
    def extract_member_inventory(self) -> Dict[str, MemberMark]:
        """Extract member mark/section list tables from early pages"""
        inventory = {}
        
        # Check first 10 pages for inventory tables/lists
        import fitz
        doc = fitz.open(self.pdf_path)
        for page_num in range(min(10, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            
            # 1. Try PyMuPDF's built-in table detection
            try:
                tables = page.find_tables()
                for table in tables:
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
                    
                    # If we found likely columns, process the table
                    if potential_mark_cols and potential_section_cols:
                        for _, row in df.iterrows():
                            mark_val = str(row.iloc[potential_mark_cols[0]]).strip()
                            section_val = str(row.iloc[potential_section_cols[0]]).strip()
                            
                            if mark_val and section_val and mark_val != 'nan' and section_val != 'nan':
                                evidence = Evidence(
                                    page_index=page_num,
                                    bbox=(table.bbox.x0, table.bbox.y0, table.bbox.x1-table.bbox.x0, table.bbox.y1-table.bbox.y0),
                                    extracted_text=f"{mark_val} - {section_val}",
                                    method='vector_text'
                                )
                                inventory[mark_val] = MemberMark(mark_id=mark_val, section=section_val, evidence=evidence)
            except:
                pass

            # 2. Heuristic fallback for non-tabular text (like Page 2, 3, 4 in some drawings)
            # Look for lines that look like: Mark [SomeRevision] [Qty] ...
            # Pattern: mark ID (often numeric prefix or specific letters) followed by some spaces
            if not inventory or page_num in [2, 3, 4]:
                # Regex for common steel marks: 104-B001B, 105-C101C, etc.
                mark_pattern = r'\b(\d{3,}[A-Z]?-[A-Z]\d{3,}[A-Z]?)\b'
                found_marks = re.findall(mark_pattern, text)
                for mark in found_marks:
                    if mark not in inventory:
                        inventory[mark] = MemberMark(
                            mark_id=mark, 
                            section="UNKNOWN (Regex)", 
                            evidence=Evidence(page_index=page_num, bbox=(0,0,0,0), extracted_text=mark, method='heuristic')
                        )

        doc.close()
        self.member_inventory = inventory
        return inventory
    
    def classify_page(self, page_idx: int, page_text: str = "") -> str:
        """Classify page type based on content and structure"""
        # If no text provided, we'll need to extract it
        if not page_text:
            try:
                import fitz
                doc = fitz.open(self.pdf_path)
                if page_idx < len(doc):
                    page_text = doc[page_idx].get_text().lower()
                doc.close()
            except:
                page_text = ""
        
        # Keywords for different page types
        metadata_keywords = ['title', 'sheet', 'drawing', 'project', 'revision', 'date', 'client', 'contractor', 'transmittal']
        inventory_keywords = ['mark', 'piece', 'member', 'list', 'summary', 'quantity', 'bill of materials', 'spec', 'shape']
        plan_keywords = ['plan', 'elevation', 'layout', 'assembly', 'general', 'overview', 'arrangement', 'key plan']
        member_keywords = ['detail', 'detailing', 'connection', 'joint', 'fabrication', 'weld', 'bolt', 'plate', 'beam', 'column', 'hss', 'stiffener']
        section_keywords = ['section', 'cut', 'view', 'detail', 'cross-section', 'elevation']
        
        # Count occurrences of keywords
        metadata_score = sum(1 for kw in metadata_keywords if kw in page_text)
        inventory_score = sum(3 for kw in inventory_keywords if kw in page_text) # Boost inventory
        plan_score = sum(1 for kw in plan_keywords if kw in page_text)
        member_score = sum(1 for kw in member_keywords if kw in page_text)
        section_score = sum(1 for kw in section_keywords if kw in page_text)
        
        # Manual overrides for inventory - usually contains lots of marks and small words
        if 'SUPERMETAL STRUCTURES' in page_text.upper() and 'MARK' in page_text.upper() and 'REF:DES' in page_text.upper():
             inventory_score += 10
             
        # Member details usually have "Tekla Structures" and specific component names
        if 'Tekla Structures' in page_text and ('W14X' in page_text or 'W30X' in page_text or 'W12X' in page_text):
             member_score += 5
             
        scores = {
            'metadata': metadata_score,
            'inventory': inventory_score,
            'plan': plan_score,
            'member_detail': member_score,
            'section_view': section_score
        }
        
        # Return the highest scoring classification
        return max(scores, key=scores.get)
    
    def extract_member_details(self, page_idx: int) -> List[Component]:
        """Extract components from member detail pages"""
        components = []
        
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            
            if page_idx >= len(doc):
                doc.close()
                return components
                
            page = doc[page_idx]
            text = page.get_text()
            
            # Patterns for different component types
            patterns = {
                'bolt': [
                    r'(\d+)\s*x?\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+BOLT',
                    r'BOLT\s+(\d+)\s+x\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+BOLTS?',
                ],
                'plate': [
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+PLATE',
                    r'PLATE\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+x\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+PLATE',
                ],
                'angle': [
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+ANGLE',
                    r'ANGLE\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
                    r'L\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
                ],
                'stiffener': [
                    r'STIFFENER',
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s*x\s*(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+STIFF',
                ],
                'weld': [
                    r'(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)\s+WELD',
                    r'WELD\s+(\d{1,2}[\"\'\\\"]?-?\d*[\"\'\\\"]?)',
                    r'FILLET\s+WELD',
                ]
            }
            
            for comp_type, comp_patterns in patterns.items():
                for pattern in comp_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            desc = ' x '.join([str(x) for x in match if x and str(x).strip()])
                        else:
                            desc = str(match)
                            
                        if not desc.strip():
                            continue
                            
                        # Find the bounding box for this match
                        text_instances = page.search_for(desc)
                        if text_instances:
                            bbox = text_instances[0]  # Take first occurrence
                            evidence = Evidence(
                                page_index=page_idx,
                                bbox=(bbox.x0, bbox.y0, bbox.x1 - bbox.x0, bbox.y1 - bbox.y0),  # x, y, w, h format
                                extracted_text=desc,
                                method='vector_text',
                                confidence=1.0
                            )
                        else:
                            evidence = None
                        
                        component = Component(
                            component_type=comp_type,
                            description=desc,
                            evidence=evidence
                        )
                        components.append(component)
            
            doc.close()
        except Exception as e:
            self.logger.warning(f"Error extracting details from page {page_idx}: {e}")
        
        return components
    
    def detect_section_cuts(self, page_idx: int) -> List[SectionCut]:
        """Detect section cuts (A-A, B-B, etc.) on a page"""
        section_cuts = []
        
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            
            if page_idx >= len(doc):
                doc.close()
                return section_cuts
                
            page = doc[page_idx]
            text = page.get_text()
            
            # Pattern for section cuts like A-A, B-B, etc.
            pattern = r'\b([A-Z])-([A-Z])\b'
            matches = re.findall(pattern, text)
            
            for match in matches:
                if len(match) >= 2:
                    name = f"{match[0]}-{match[1]}"
                    
                    # Find the position of this section cut in the text
                    search_text = name
                    text_instances = page.search_for(search_text)
                    
                    for inst in text_instances:
                        evidence = Evidence(
                            page_index=page_idx,
                            bbox=(inst.x0, inst.y0, inst.x1 - inst.x0, inst.y1 - inst.y0),  # x, y, w, h format
                            extracted_text=name,
                            method='vector_text',
                            confidence=1.0
                        )
                        
                        section_cut = SectionCut(
                            name=name,
                            page_index=page_idx,
                            bbox=(inst.x0, inst.y0, inst.x1 - inst.x0, inst.y1 - inst.y0),
                            evidence=evidence
                        )
                        section_cuts.append(section_cut)
            
            doc.close()
        except Exception as e:
            self.logger.warning(f"Error detecting section cuts on page {page_idx}: {e}")
        
        return section_cuts
    
    def process_page_with_ocr_if_needed(self, page_idx: int) -> str:
        """Process a page, using OCR if vector text is insufficient"""
        import fitz
        doc = fitz.open(self.pdf_path)
        
        if page_idx >= len(doc):
            doc.close()
            return ""
        
        page = doc[page_idx]
        
        # Get vector text first
        vector_text = page.get_text()
        
        # If the page has little text (potential scanned page) or low confidence elements, use OCR
        text_ratio = len(vector_text) / (page.rect.width * page.rect.height) if (page.rect.width * page.rect.height) > 0 else 0
        
        if len(vector_text.strip()) < 50 or text_ratio < 0.001:  # Likely a scanned page
            # Convert page to image and OCR
            try:
                # Render page to image
                mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Create PIL image from bytes
                import io
                pil_img = Image.open(io.BytesIO(img_data))
                
                # Perform OCR
                ocr_text, confidence = self.ocr_captor.ocr_image(pil_img)
                
                doc.close()
                
                # Return OCR text if it's better than vector text
                if len(ocr_text.strip()) > len(vector_text.strip()):
                    return ocr_text
                else:
                    return vector_text
            except Exception as e:
                self.logger.warning(f"OCR failed for page {page_idx}, using vector text: {e}")
                doc.close()
                return vector_text
        else:
            doc.close()
            return vector_text
    
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
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            doc.close()
        except:
            total_pages = 10  # Fallback estimate
        
        for page_idx in range(total_pages):
            # Get page content (using OCR if needed)
            page_content = self.process_page_with_ocr_if_needed(page_idx)
            
            # Classify page
            page_type = self.classify_page(page_idx, page_content.lower())
            
            # Extract additional data based on page type
            components = []
            sections = []
            
            if page_type == 'member_detail':
                components = self.extract_member_details(page_idx)
            
            sections = self.detect_section_cuts(page_idx)
            self.section_cuts.extend(sections)
            
            # Store parsed page
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
        
        # Step 4: Compile final results
        result = {
            'document_info': {
                'filename': self.pdf_path.name,
                'total_pages': total_pages,
                'parsed_date': pd.Timestamp.now().isoformat(),
                'ocr_backend_used': self.ocr_captor.backend
            },
            'project_metadata': self.project_metadata,
            'member_inventory': {k: asdict(v) for k, v in self.member_inventory.items() if v.evidence},
            'section_cuts': [asdict(sc) for sc in self.section_cuts if sc.evidence],
            'pages': [asdict(pp) for pp in self.parsed_pages]
        }
        
        self.logger.info("Parsing complete!")
        return result
    
    def export_results(self, output_path: str, format: str = 'jsonl'):
        """Export results to JSON or JSONL with evidence tracking"""
        results = self.parse_document()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'jsonl':
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write document info as first line
                f.write(json.dumps({
                    'type': 'document_info',
                    'data': results['document_info']
                }) + '\n')
                
                # Write project metadata
                f.write(json.dumps({
                    'type': 'project_metadata',
                    'data': results['project_metadata']
                }) + '\n')
                
                # Write each inventory item
                for mark_id, member_data in results['member_inventory'].items():
                    f.write(json.dumps({
                        'type': 'member_inventory',
                        'data': member_data
                    }) + '\n')
                
                # Write each page
                for page_data in results['pages']:
                    f.write(json.dumps({
                        'type': 'page_data',
                        'data': page_data
                    }) + '\n')
                
                # Write section cuts
                for section_cut in results['section_cuts']:
                    f.write(json.dumps({
                        'type': 'section_cut',
                        'data': section_cut
                    }) + '\n')
        else:  # JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Results exported to {output_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python steel_drawing_parser_v2.py <input_pdf_path> <output_json_path> [ocr_backend]")
        print("OCR backends: tesseract (default), paddle")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_json = sys.argv[2]
    ocr_backend = sys.argv[3] if len(sys.argv) > 3 else 'tesseract'
    
    if not os.path.exists(input_pdf):
        print(f"Error: Input file {input_pdf} does not exist")
        sys.exit(1)
    
    processor = SteelDrawingProcessor(input_pdf, ocr_backend=ocr_backend)
    processor.export_results(output_json, format='jsonl')


if __name__ == "__main__":
    main()