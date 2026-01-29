import streamlit as st
import pandas as pd
from PIL import Image
import numpy as np
import ocr_utils
import tempfile
import os

st.set_page_config(page_title="OCR 辨識系統", layout="wide")

st.title("🪪 證件 OCR 辨識系統 (ID/Passport)")
st.markdown("""
支援格式：
1. **台灣身分證** (正反面)
2. **護照** (台灣、中國、澳門及其他國家)
   - 自動提取中文姓名 (若有)
   - 自動提取 MRZ 資訊 (姓名、號碼)
""")

# Input Method
input_method = st.radio("選擇輸入方式", ["上傳圖片", "拍照"])

image_file = None

if input_method == "上傳圖片":
    image_file = st.file_uploader("上傳證件圖片", type=["jpg", "png", "jpeg"])
else:
    image_file = st.camera_input("拍攝證件")

if image_file:
    # Display Image
    image = Image.open(image_file)
    st.image(image, caption="預覽圖片", use_column_width=True)
    
    if st.button("開始辨識"):
        with st.spinner("正在辨識中... (Processing)"):
            try:
                # Save to temp file for path-based processing or pass bytes
                # rapidocr accepts numpy array, so we can convert directly without saving
                img_array = np.array(image.convert('RGB'))
                
                # We need to modify ocr_utils to accept array directly or handle it
                # Looking at my ocr_utils.py, preprocess_image takes 'image_file' and does Image.open()
                # I should modify ocr_utils to accept loaded image or update app to pass file path.
                # Since image_file is a BytesIO object, Image.open works.
                # But inside ocr_utils.preprocess_image, it expects a file path or file-like object.
                # Let's handle it by creating a temp file to be safe and robust for cv2 based utils if any.
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    image.convert('RGB').save(tmp, format='JPEG')
                    tmp_path = tmp.name
                
                # Process
                results = ocr_utils.process_document(tmp_path)
                
                # Cleanup
                os.remove(tmp_path)
                
                st.success("辨識完成! (Success)")
                
                # 1. Standardized Form (Check-in Data)
                st.markdown("### 📝 入住資料 (Check-in Form)")
                st.info("請核對以下資訊 (Please verify)")
                
                std_data = results.get("Standardized", {})
                if not std_data: # Fallback for old return format safety
                     std_data = results if "Standardized" not in results else {}

                if std_data:
                    c1, c2 = st.columns(2)
                    keys = list(std_data.keys())
                    half = (len(keys) + 1) // 2
                    
                    with c1:
                        for key in keys[:half]:
                            st.text_input(key, value=str(std_data[key]), key=f"std_{key}")
                    with c2:
                        for key in keys[half:]:
                            st.text_input(key, value=str(std_data[key]), key=f"std_{key}")
                
                st.divider()

                # 2. Detailed Extraction (Raw Fields)
                st.markdown("### 🔍 原始提取資料 (Raw Detailed Data)")
                raw_data = results.get("Detailed", {})
                
                if raw_data:
                    # Filter out Raw Lines for clean display
                    display_data = {k: v for k, v in raw_data.items() if k != 'Raw Lines'}
                    st.write(display_data)

                with st.expander("查看完整 OCR 文字 (Raw OCR Lines)"):
                     st.write(raw_data.get("Raw Lines", []))
                    
            except Exception as e:
                st.error(f"發生錯誤: {e}")
                st.exception(e)

st.markdown("---")
st.caption("Powered by RapidOCR & Streamlit")
