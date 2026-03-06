import os
import cv2
import fitz  # PyMuPDF
from ultralytics import YOLO
from PIL import Image
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

def test_inference_with_tiling(pdf_path, model_path, output_dir):
    # Load SAHI model
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='ultralytics',
        model_path=model_path,
        confidence_threshold=0.01, # Low for testing
        device='cpu'
    )
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Open PDF
    doc = fitz.open(pdf_path)
    print(f"Processing PDF: {pdf_path} ({len(doc)} pages)")
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # 300 DPI for high detail
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_path = os.path.join(output_dir, f"page_{page_num}.png")
        pix.save(img_path)
        
        # Run Sliced (Tiling) Inference
        print(f"Running tiled inference on page {page_num+1}...")
        result = get_sliced_prediction(
            img_path,
            detection_model,
            slice_height=640,
            slice_width=640,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2
        )
        
        # Save annotated image
        result.export_visuals(export_dir=output_dir, file_name=f"tiled_detected_page_{page_num}")
        
        # Summary
        counts = {}
        for pred in result.object_prediction_list:
            name = pred.category.name
            counts[name] = counts.get(name, 0) + 1
            
        print(f"Page {page_num+1} Tiled Detections: {counts if counts else 'None'}")

if __name__ == "__main__":
    PDF = "uploads/Steel submittal test.pdf"
    MODEL = "training/runs/detect/train/weights/best.pt"
    OUT = "inference_tiled_results"
    
    test_inference_with_tiling(PDF, MODEL, OUT)
