import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import json
import tempfile
import os
from pathlib import Path
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
    st.warning("pdf2image not available - PDF preview will be limited")
import base64
from io import BytesIO
import re

# Import our processor
try:
    from steel_drawing_parser_v2 import SteelDrawingProcessor, Evidence, MemberMark, Component, SectionCut, ParsedPage
    PROCESSOR_AVAILABLE = True
except ImportError as e:
    st.error(f"Processor import error: {e}")
    PROCESSOR_AVAILABLE = False


def render_uploaded_file_preview(uploaded_file):
    """Render a preview of the uploaded PDF file"""
    if uploaded_file is not None and convert_from_path is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_pdf_path = tmp_file.name
        
        try:
            # Convert first few pages to images for preview
            images = convert_from_path(temp_pdf_path, first_page=1, last_page=min(3, 10), dpi=100)
            
            st.subheader("PDF Preview")
            cols = st.columns(min(len(images), 3))
            for i, img in enumerate(images):
                with cols[i % len(cols)]:
                    st.image(img, caption=f"Page {i+1}", use_column_width=True)
            
            # Clean up
            os.unlink(temp_pdf_path)
            return temp_pdf_path
        except Exception as e:
            st.error(f"Error converting PDF: {e}")
            return None
    elif uploaded_file is not None:
        # Just show the file info if pdf2image isn't available
        st.info(f"Uploaded file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        return None
    return None


def display_parsed_results(results):
    """Display the parsed results in the Streamlit UI"""
    st.header("Parsed Results")
    
    # Document Info
    st.subheader("Document Information")
    doc_info = results.get('document_info', {})
    st.json(doc_info)
    
    # Project Metadata
    st.subheader("Project Metadata")
    metadata = results.get('project_metadata', {})
    if metadata:
        st.json(metadata)
    else:
        st.info("No project metadata found")
    
    # Member Inventory
    st.subheader("Member Inventory")
    inventory = results.get('member_inventory', {})
    if inventory:
        # Create a DataFrame for better visualization
        inventory_data = []
        for mark_id, data in inventory.items():
            inv_row = {
                'MARK': data.get('mark_id', ''),
                'SECTION': data.get('section', ''),
                'QUANTITY': data.get('quantity', ''),
            }
            # Add evidence info if available
            evidence = data.get('evidence', {})
            if evidence:
                inv_row.update({
                    'PAGE': evidence.get('page_index', ''),
                    'CONFIDENCE': evidence.get('confidence', '')
                })
            inventory_data.append(inv_row)
        
        df_inventory = pd.DataFrame(inventory_data)
        st.dataframe(df_inventory)
        
        # Show raw inventory data
        with st.expander("Raw Inventory Data"):
            st.json(inventory)
    else:
        st.info("No member inventory found")
    
    # Section Cuts
    st.subheader("Section Cuts")
    section_cuts = results.get('section_cuts', [])
    if section_cuts:
        section_cut_data = []
        for sc in section_cuts:
            sc_row = {
                'NAME': sc.get('name', ''),
                'PAGE': sc.get('page_index', ''),
                'X': sc.get('bbox', [0])[0] if sc.get('bbox') else '',
                'Y': sc.get('bbox', [0, 0])[1] if sc.get('bbox') else '',
                'WIDTH': sc.get('bbox', [0, 0, 0])[2] if sc.get('bbox') else '',
                'HEIGHT': sc.get('bbox', [0, 0, 0, 0])[3] if sc.get('bbox') else '',
            }
            section_cut_data.append(sc_row)
        
        df_sections = pd.DataFrame(section_cut_data)
        st.dataframe(df_sections)
    else:
        st.info("No section cuts detected")
    
    # Pages Analysis
    st.subheader("Page Analysis")
    pages = results.get('pages', [])
    if pages:
        # Create a summary table
        page_summary = []
        for page in pages:
            pg_row = {
                'PAGE_INDEX': page.get('page_index', ''),
                'TYPE': page.get('page_type', ''),
                'CONTENT_LENGTH': len(page.get('content', '')),
            }
            page_summary.append(pg_row)
        
        df_pages = pd.DataFrame(page_summary)
        st.dataframe(df_pages)
        
        # Allow user to select a page to view details
        if len(pages) > 0:
            selected_page_idx = st.selectbox("Select a page to view details", 
                                           options=list(range(len(pages))), 
                                           format_func=lambda x: f"Page {pages[x]['page_index']} ({pages[x]['page_type']})")
            
            if selected_page_idx is not None:
                selected_page = pages[selected_page_idx]
                st.subheader(f"Details for Page {selected_page['page_index']} ({selected_page['page_type']})")
                
                # Display page content
                with st.expander("Page Content"):
                    st.text_area("Content", value=selected_page['content'], height=200)
                
                # Display extracted data
                extracted_data = selected_page.get('extracted_data', {})
                if extracted_data.get('components'):
                    st.subheader("Components Found")
                    components = extracted_data['components']
                    comp_data = []
                    for comp in components:
                        comp_row = {
                            'TYPE': comp.get('component_type', ''),
                            'DESCRIPTION': comp.get('description', ''),
                        }
                        evidence = comp.get('evidence', {})
                        if evidence:
                            comp_row.update({
                                'PAGE': evidence.get('page_index', ''),
                                'CONFIDENCE': evidence.get('confidence', '')
                            })
                        comp_data.append(comp_row)
                    
                    if comp_data:
                        df_comps = pd.DataFrame(comp_data)
                        st.dataframe(df_comps)
                
                if extracted_data.get('section_cuts'):
                    st.subheader("Section Cuts on this Page")
                    section_cuts_pg = extracted_data['section_cuts']
                    sc_data = []
                    for sc in section_cuts_pg:
                        sc_row = {
                            'NAME': sc.get('name', ''),
                        }
                        evidence = sc.get('evidence', {})
                        if evidence:
                            sc_row.update({
                                'PAGE': evidence.get('page_index', ''),
                                'X': evidence.get('bbox', [0])[0] if evidence.get('bbox') else '',
                                'Y': evidence.get('bbox', [0, 0])[1] if evidence.get('bbox') else '',
                            })
                        sc_data.append(sc_row)
                    
                    if sc_data:
                        df_sc = pd.DataFrame(sc_data)
                        st.dataframe(df_sc)
    else:
        st.info("No pages analyzed")


def main():
    st.set_page_config(page_title="Steel Shop Drawing Parser", layout="wide")
    st.title("🏗️ Steel Shop Drawing Parser")
    st.markdown("""
    Upload a steel shop drawing PDF to extract structured data:
    - Project metadata
    - Member inventory (MARK, SECTION, QTY)
    - Component details (bolts, plates, angles, etc.)
    - Section cuts (A-A, B-B, etc.)
    """)
    
    if not PROCESSOR_AVAILABLE:
        st.error("Required modules are not available. Please run: pip install -r requirements_new.txt")
        st.stop()
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])
    
    if uploaded_file is not None:
        # Save to workspace instead of temp to avoid early deletion
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        temp_pdf_path = os.path.join(uploads_dir, uploaded_file.name)
        
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Display file preview
        if convert_from_path is not None:
            try:
                # Convert first few pages to images for preview
                images = convert_from_path(temp_pdf_path, first_page=1, last_page=min(3, 10), dpi=100)
                
                st.subheader("PDF Preview")
                cols = st.columns(min(len(images), 3))
                for i, img in enumerate(images):
                    with cols[i % len(cols)]:
                        st.image(img, caption=f"Page {i+1}", use_column_width=True)
            except Exception as e:
                st.error(f"Error converting PDF: {e}")
        else:
            st.info(f"Uploaded file: {uploaded_file.name} ({uploaded_file.size} bytes)")
            
        # OCR Backend Selection
        st.subheader("Processing Options")
        ocr_backend = st.selectbox("OCR Backend", ["tesseract", "paddle"], 
                                 help="Select OCR engine for text extraction from scanned documents")
        
        # Process button
        if st.button("Process PDF", type="primary"):
            with st.spinner("Processing PDF... This may take a few minutes."):
                try:
                    # Create processor instance
                    processor = SteelDrawingProcessor(temp_pdf_path, ocr_backend=ocr_backend)
                    
                    # Parse the document
                    results = processor.parse_document()
                    
                    # Display results
                    display_parsed_results(results)
                    
                    # Provide download option for results
                    jsonl_output = json.dumps(results, indent=2)
                    b64 = base64.b64encode(jsonl_output.encode()).decode()
                    href = f'<a href="data:file/jsonl;base64,{b64}" download="steel_analysis_results.json">Download Full Results (JSON)</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Error processing PDF: {e}")
                    st.exception(e)
            
            # Note: We keep the file in uploads/ for verification, or delete it here if preferred.
            # os.unlink(temp_pdf_path)


if __name__ == "__main__":
    main()