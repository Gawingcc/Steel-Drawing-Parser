#!/usr/bin/env python3
"""
Dependency installer for Steel Shop Drawing Parser
Handles installation of all required packages with proper error handling
"""

import subprocess
import sys
import platform
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"[INFO] {description}")
    print(f"[CMD] {cmd}")
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=True
        )
        print("[SUCCESS] Command completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with return code {e.returncode}")
        print(f"[STDOUT] {e.stdout}")
        print(f"[STDERR] {e.stderr}")
        return False


def install_dependencies():
    """Install all required dependencies"""
    print("Steel Shop Drawing Parser - Dependency Installer")
    print("=" * 50)
    
    # Check if running on Windows
    is_windows = platform.system().lower() == 'windows'
    
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    
    # Basic dependencies that should work
    basic_reqs = [
        "pip install --upgrade pip",
        "pip install --break-system-packages pandas numpy pillow pytesseract pdf2image opencv-python"
    ]
    
    for req in basic_reqs:
        success = run_command(req, f"Installing basic requirements: {req}")
        if not success:
            print(f"[WARNING] Failed to install basic requirement: {req}")
    
    # Try to install Docling
    docling_success = run_command(
        "pip install --break-system-packages docling==2.0.0",
        "Installing Docling (document understanding library)"
    )
    
    if not docling_success:
        print("[WARNING] Docling installation failed, continuing with basic PDF processing")
    
    # Try to install PaddleOCR
    paddle_success = run_command(
        "pip install --break-system-packages paddleocr==2.7.3",
        "Installing PaddleOCR"
    )
    
    if not paddle_success:
        print("[WARNING] PaddleOCR installation failed, will use Tesseract as fallback")
    
    # Install Streamlit
    streamlit_success = run_command(
        "pip install --break-system-packages streamlit==1.30.0",
        "Installing Streamlit"
    )
    
    if not streamlit_success:
        print("[ERROR] Streamlit installation failed - UI will not be available")
        return False
    
    # Install transformers and torch if needed for advanced features
    run_command(
        "pip install --break-system-packages torch==2.1.0 transformers==4.34.0",
        "Installing PyTorch and Transformers (optional)"
    )
    
    print("\nDependency installation complete!")
    print("\nTo run the application:")
    print("1. For the console parser: python steel_drawing_parser_v2.py <input.pdf> <output.jsonl>")
    print("2. For the web UI: streamlit run app_simple.py")
    
    return True


def verify_installation():
    """Verify that critical dependencies are installed"""
    print("\nVerifying installations...")
    
    imports_to_check = [
        ("pandas", "pandas"),
        ("numpy", "numpy"), 
        ("PIL", "Pillow"),
        ("cv2", "opencv-python"),
        ("pytesseract", "pytesseract"),
        ("pdf2image", "pdf2image")
    ]
    
    missing_imports = []
    
    for module, name in imports_to_check:
        try:
            __import__(module)
            print(f"✓ {name} available")
        except ImportError:
            print(f"✗ {name} NOT available")
            missing_imports.append((module, name))
    
    # Try Docling
    try:
        import docling
        print("✓ Docling available")
    except ImportError:
        print("? Docling NOT available (this is OK, basic PDF processing will be used)")
    
    # Try PaddleOCR
    try:
        import paddleocr
        print("✓ PaddleOCR available")
    except ImportError:
        print("? PaddleOCR NOT available (Tesseract will be used as fallback)")
    
    # Try Streamlit
    try:
        import streamlit
        print("✓ Streamlit available")
    except ImportError:
        print("✗ Streamlit NOT available - UI will not work")
        return False
    
    if missing_imports:
        print(f"\nWarning: {len(missing_imports)} critical dependencies are missing.")
        print("Please install them manually or run this script again.")
        return False
    
    print("\n✓ All critical dependencies verified!")
    return True


if __name__ == "__main__":
    print("Starting dependency installation...")
    success = install_dependencies()
    
    if success:
        verify_installation()
        print("\nInstallation process complete!")
    else:
        print("\nInstallation had issues. Some features may not work.")
        print("Please check error messages above and try installing missing packages manually.")