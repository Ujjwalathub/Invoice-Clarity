"""
Data Preprocessing Pipeline for OCR + LLM Architecture

This module provides two critical preprocessing phases:
1. Image Preprocessing: Optimizes raw images for EasyOCR vision inference
2. Text Preprocessing: Cleans and sorts OCR output for LLM reasoning

Author: OCR Backend Team
"""

import cv2
import numpy as np
import re
from typing import List, Tuple


def preprocess_image_for_ocr(image_bytes: bytes) -> bytes:
    """
    Takes raw image bytes, applies computer vision filters to optimize 
    for OCR, and returns the processed image bytes.
    
    Pipeline:
    1. Resizing: Caps max dimension to 1500px to prevent VRAM overflow
    2. Grayscaling: Reduces memory footprint (3 channels → 1 channel)
    3. Adaptive Thresholding: Converts to binary (black/white) to eliminate shadows
    4. Denoising: Removes scanner dust and camera artifacts
    
    Args:
        image_bytes: Raw image data as bytes
        
    Returns:
        Preprocessed image as PNG bytes
        
    Raises:
        ValueError: If image cannot be decoded or processed
    """
    try:
        # 1. Convert bytes to numpy array, then to OpenCV image format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image. Invalid image format.")

        # 2. Resizing (Cap max dimension to 1500px to save VRAM)
        max_dimension = 1500
        height, width = img.shape[:2]
        if max(height, width) > max_dimension:
            scaling_factor = max_dimension / float(max(height, width))
            img = cv2.resize(
                img, 
                None, 
                fx=scaling_factor, 
                fy=scaling_factor, 
                interpolation=cv2.INTER_AREA
            )

        # 3. Grayscale Conversion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 4. Adaptive Thresholding (Handles uneven lighting)
        # Block size of 21 and C value of 10 are optimized for document text
        binary = cv2.adaptiveThreshold(
            gray, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 
            10
        )

        # 5. Encode back to bytes so EasyOCR can read it natively
        success, encoded_image = cv2.imencode('.png', binary)
        if not success:
            raise ValueError("Failed to encode preprocessed image.")
            
        return encoded_image.tobytes()
        
    except Exception as e:
        raise ValueError(f"Image preprocessing failed: {str(e)}")


def clean_and_sort_ocr_text(raw_results: List[Tuple]) -> str:
    """
    Sorts EasyOCR bounding boxes top-to-bottom and cleans the strings.
    
    Pipeline:
    1. Spatial Sorting: Orders text by Y-coordinate (top to bottom)
    2. Noise Filtering: Removes low-confidence reads and non-alphanumeric garbage
    3. Concatenation: Normalizes whitespace for optimal LLM token usage
    
    Args:
        raw_results: EasyOCR output with detail=1
                    Format: [([[x,y],[x,y],[x,y],[x,y]], 'text', confidence), ...]
        
    Returns:
        Clean, sorted text string ready for LLM inference
    """
    if not raw_results:
        return ""
    
    # 1. Sort by Y-coordinate of the top-left corner of the bounding box
    # bbox[0][0][1] gets the Y value of the top-left point
    sorted_results = sorted(raw_results, key=lambda x: x[0][0][1])
    
    clean_lines = []
    for bbox, text, confidence in sorted_results:
        # Ignore extremely low confidence reads (garbage text)
        if confidence < 0.25:
            continue
            
        # 2. Noise Filtering: Remove random single symbols
        # Keep text if it contains at least one letter or number
        if re.search(r'[A-Za-z0-9]', text):
            # Strip excessive whitespaces inside the string
            clean_text = " ".join(text.split())
            clean_lines.append(clean_text)
            
    # 3. Concatenation with normalized whitespace
    return "\n".join(clean_lines)


def preprocess_image_advanced(
    image_bytes: bytes, 
    max_dimension: int = 1500,
    denoise: bool = True,
    sharpen: bool = False
) -> bytes:
    """
    Advanced image preprocessing with configurable options.
    
    This variant adds optional denoising and sharpening for particularly
    degraded documents (faxes, photocopies, heavily folded receipts).
    
    Args:
        image_bytes: Raw image data as bytes
        max_dimension: Maximum pixel dimension (default: 1500)
        denoise: Apply Gaussian blur to remove noise (default: True)
        sharpen: Apply unsharp mask to enhance edges (default: False)
        
    Returns:
        Preprocessed image as PNG bytes
    """
    try:
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image.")

        # Resize
        height, width = img.shape[:2]
        if max(height, width) > max_dimension:
            scaling_factor = max_dimension / float(max(height, width))
            img = cv2.resize(
                img, 
                None, 
                fx=scaling_factor, 
                fy=scaling_factor, 
                interpolation=cv2.INTER_AREA
            )

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Optional denoising (reduces salt-and-pepper noise)
        if denoise:
            gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # Optional sharpening (enhances edge contrast)
        if sharpen:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            gray = cv2.filter2D(gray, -1, kernel)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 
            10
        )

        # Encode to bytes
        success, encoded_image = cv2.imencode('.png', binary)
        if not success:
            raise ValueError("Failed to encode preprocessed image.")
            
        return encoded_image.tobytes()
        
    except Exception as e:
        raise ValueError(f"Advanced image preprocessing failed: {str(e)}")


def validate_ocr_output(raw_results: List[Tuple], min_text_length: int = 10) -> bool:
    """
    Validates that OCR output contains meaningful text.
    
    Args:
        raw_results: EasyOCR output with detail=1
        min_text_length: Minimum total character length for valid output
        
    Returns:
        True if output contains sufficient readable text, False otherwise
    """
    if not raw_results:
        return False
    
    total_text = "".join([text for _, text, conf in raw_results if conf > 0.25])
    alphanumeric_count = sum(1 for char in total_text if char.isalnum())
    
    return alphanumeric_count >= min_text_length
