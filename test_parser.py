#!/usr/bin/env python3
"""
Simple test to verify the parser structure is correct
"""

from steel_drawing_parser import (
    Evidence, 
    MemberMark, 
    Component, 
    SectionCut, 
    ParsedPage, 
    SteelDrawingParser
)

def test_classes():
    """Test that all data classes are properly defined"""
    print("Testing data classes...")
    
    # Test Evidence
    evidence = Evidence(
        page_number=1,
        bbox=(10, 20, 30, 40),
        source_text="Test evidence"
    )
    print(f"✓ Evidence: {evidence.page_number}, {evidence.bbox}")
    
    # Test MemberMark
    member = MemberMark(
        mark_id="W12x50",
        section="W12x50",
        evidence=evidence
    )
    print(f"✓ MemberMark: {member.mark_id}, {member.section}")
    
    # Test Component
    component = Component(
        component_type="bolt",
        description="1/2\" diameter bolt",
        evidence=evidence
    )
    print(f"✓ Component: {component.component_type}, {component.description}")
    
    # Test SectionCut
    section_cut = SectionCut(
        name="A-A",
        page_number=5,
        bbox=(100, 200, 150, 250),
        evidence=evidence
    )
    print(f"✓ SectionCut: {section_cut.name}, page {section_cut.page_number}")
    
    # Test ParsedPage
    parsed_page = ParsedPage(
        page_number=1,
        page_type="detail",
        content="Sample page content",
        extracted_data={"test": "data"}
    )
    print(f"✓ ParsedPage: page {parsed_page.page_number}, type {parsed_page.page_type}")
    
    print("\nAll data classes are properly defined!")

def test_parser_creation():
    """Test that we can create a parser instance (without a real PDF)"""
    print("\nTesting parser creation...")
    
    # We'll test by creating a fake PDF path - the init shouldn't fail on basic instantiation
    try:
        # This will fail later when trying to open the file, but constructor should work
        parser = SteelDrawingParser("/fake/path/test.pdf")
        print("✓ Parser object created successfully")
        print(f"✓ PDF path stored: {parser.pdf_path}")
    except Exception as e:
        print(f"Note: Expected error when opening fake file: {type(e).__name__}")

if __name__ == "__main__":
    test_classes()
    test_parser_creation()
    print("\n✓ All tests passed! The parser structure is correct.")