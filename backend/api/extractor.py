import io
import json
import re
import time
from typing import List, Tuple

import easyocr
import numpy as np
import ollama
from PIL import Image

from .preprocessing import (
    preprocess_image_for_ocr,
    clean_and_sort_ocr_text,
    validate_ocr_output
)

# Initialize EasyOCR reader once per process to avoid repeated model loads.
# GPU mode is enabled so the backend can leverage RTX 3050 VRAM during OCR.
reader = easyocr.Reader(['en'], gpu=True)

ALLOWED_KEYS = [
    'vendor_name',
    'invoice_number',
    'date',
    'total_amount',
]

SYSTEM_PROMPT = (
    "You are a data extraction engine. "
    "I will provide raw OCR text from an invoice. "
    "Extract only the following fields: vendor_name, invoice_number, date, and total_amount. "
    "Return exactly one JSON object with those keys. "
    "If a field cannot be found, return null for that key. "
    "Do not add markdown, explanation, or any extra keys. "
    "Do not include conversational filler. "
)


def get_bbox_top_left(bbox: List[Tuple[float, float]]) -> Tuple[float, float]:
    x_coords = [int(point[0]) for point in bbox]
    y_coords = [int(point[1]) for point in bbox]
    return min(x_coords), min(y_coords)


def aggregate_ocr_text(raw_results: List[str]) -> str:
    """Concatenate OCR tokens into a single raw text block."""
    return " ".join(raw_results).strip()


def regex_extract_invoice_fields(raw_text: str) -> dict:
    """Fallback extraction using regex heuristics when LLM is unavailable or fails."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    vendor_name = None
    invoice_number = None
    date = None
    total_amount = None

    for line in lines:
        if not re.search(r'invoice|date|total|bill|due|amount', line, re.IGNORECASE):
            vendor_name = line
            break
    if not vendor_name and lines:
        vendor_name = lines[0]

    inv_match = re.search(r'(?:invoice\s*#?|inv\s*#?|no\.?|num\.?)\s*[:#-]?\s*([A-Z0-9-]+)', raw_text, re.IGNORECASE)
    if inv_match:
        invoice_number = inv_match.group(1)

    date_match = re.search(r'(?:date\s*[:#-]?\s*)?(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})', raw_text, re.IGNORECASE)
    if date_match:
        date = date_match.group(1)

    total_match = re.search(r'(?:total|amount due|balance due)\s*[:$€£]?\s*([$€£]?\s*\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if total_match:
        total_amount = total_match.group(1).strip()
    else:
        amounts = re.findall(r'[$€£]?\s*\d{1,3}(?:,\d{3})*\.\d{2}', raw_text)
        if amounts:
            total_amount = amounts[-1].strip()

    return {
        'vendor_name': vendor_name,
        'invoice_number': invoice_number,
        'date': date,
        'total_amount': total_amount,
    }


def extract_invoice_fields(raw_text: str) -> dict:
    """Call Ollama to format OCR output into the target invoice schema, with regex fallback."""
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': raw_text},
    ]

    try:
        response = ollama.chat(model='llama3.2', messages=messages)
        content = response.get('message', {}).get('content', '')

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            stripped = strip_markdown_json(content)
            parsed = json.loads(stripped)

        if not isinstance(parsed, dict):
            parsed = regex_extract_invoice_fields(raw_text)

        filtered = {key: parsed.get(key) if parsed.get(key) is not None else None for key in ALLOWED_KEYS}
        return filtered
    except Exception:
        # If Ollama fails, model is missing, or LLM output is unparseable, use regex fallback
        return regex_extract_invoice_fields(raw_text)


def strip_markdown_json(text: str) -> str:
    """Remove surrounding markdown fences or extra wrapper text from LLM output."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def process_image_bytes(image_bytes: bytes) -> dict:
    """
    Run EasyOCR on the provided image and extract invoice data.
    
    Pipeline:
    1. Image Preprocessing: Optimize image for OCR (resize, grayscale, binarize)
    2. OCR Inference: Extract text with bounding boxes
    3. Text Preprocessing: Sort and clean OCR output
    4. LLM Inference: Structure data into JSON schema
    """
    ocr_start = time.perf_counter()
    
    # --- PHASE 1: IMAGE PREPROCESSING ---
    # Cleans lighting, limits size to protect RTX 3050 VRAM
    try:
        optimized_image_bytes = preprocess_image_for_ocr(image_bytes)
    except ValueError as e:
        raise ValueError(f'Image preprocessing failed: {str(e)}')
    
    # --- VISION INFERENCE ---
    # Use detail=1 to get bounding box coordinates for sorting
    raw_ocr_results = reader.readtext(optimized_image_bytes, detail=1, paragraph=False)
    
    # Validate OCR output quality
    if not validate_ocr_output(raw_ocr_results):
        raise ValueError('No readable text found in the image.')
    
    # --- PHASE 2: TEXT PREPROCESSING ---
    # Sorts top-to-bottom and removes garbage symbols
    clean_text_payload = clean_and_sort_ocr_text(raw_ocr_results)
    
    if not clean_text_payload.strip():
        raise ValueError('OCR engine failed to extract meaningful text from the image.')
    
    ocr_elapsed = time.perf_counter() - ocr_start

    # --- LLM INFERENCE ---
    llm_start = time.perf_counter()
    invoice_data = extract_invoice_fields(clean_text_payload)
    llm_elapsed = time.perf_counter() - llm_start

    return {
        'data': invoice_data,
        'metadata': {
            'processing_time_seconds': round(ocr_elapsed + llm_elapsed, 3),
            'ocr_time_seconds': round(ocr_elapsed, 3),
            'llm_time_seconds': round(llm_elapsed, 3)
        }
    }
