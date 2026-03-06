import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw
import json
import os
from pathlib import Path

# Setup simple labeling UI
st.set_page_config(layout="wide")
st.title("🦞 Steel Drawing Labeler (YOLO Preparation)")

IMAGE_DIR = "projects/steel-drawing-parser/training/raw_images"
LABEL_DIR = "projects/steel-drawing-parser/training/labels"
CLASSES = ["connection", "member_mark", "bolt_table", "weld_symbol"]

if not os.path.exists(IMAGE_DIR):
    st.error("No images found in training/raw_images")
    st.stop()

images = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])
img_file = st.sidebar.selectbox("Select Image", images)

if img_file:
    img_path = os.path.join(IMAGE_DIR, img_file)
    label_path = os.path.join(LABEL_DIR, img_file.replace(".jpg", ".txt"))
    
    img = Image.open(img_path)
    w, h = img.size
    
    st.write(f"Image Size: {w}x{h}")
    st.image(img, use_column_width=True)
    
    st.sidebar.header("Instructions")
    st.sidebar.info("Since this is a headless environment, please use a local labeling tool like **LabelImg** or **CVAT** to draw boxes. I have exported the images to your workspace.")
    
    st.sidebar.subheader("Class IDs for YOLO:")
    for i, cls in enumerate(CLASSES):
        st.sidebar.write(f"{i}: {cls}")

    if st.button("Generate Template Label File"):
        with open(label_path, "w") as f:
            f.write(f"# YOLO label file for {img_file}\n")
        st.success(f"Created {label_path}")
