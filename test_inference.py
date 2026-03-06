import os
import cv2
import fitz  # PyMuPDF
from ultralytics import YOLO
from PIL import Image

def test_inference(pdf_path, model_path, output_dir):
    # Load model
    model = YOLO(model_path)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Open PDF
    doc = fitz.open(pdf_path)
    print(f"Processing PDF: {pdf_path} ({len(doc)} pages)")
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Increase resolution for better detection (300 DPI)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_path = os.path.join(output_dir, f"page_{page_num}.png")
        pix.save(img_path)
        
        # Run YOLO inference
        print(f"Running inference on page {page_num+1}...")
        results = model.predict(source=img_path, conf=0.01) # Low confidence threshold for testing
        
        # Save annotated image
        res_plotted = results[0].plot()
        out_img_path = os.path.join(output_dir, f"detected_page_{page_num}.jpg")
        cv2.imwrite(out_img_path, res_plotted)
        
        # Summary of detections
        counts = {}
        for box in results[0].boxes:
            cls = int(box.cls[0])
            name = model.names[cls]
            counts[name] = counts.get(name, 0) + 1
        
        print(f"Page {page_num+1} Detections: {counts if counts else 'None'}")

if __name__ == "__main__":
    PDF = "uploads/Steel submittal test.pdf"
    MODEL = "training/runs/detect/train/weights/best.pt"
    OUT = "inference_test_results"
    
    test_inference(PDF, MODEL, OUT)
