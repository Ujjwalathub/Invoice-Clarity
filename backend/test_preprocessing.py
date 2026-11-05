"""
Preprocessing Pipeline Test Script

This script demonstrates the impact of image and text preprocessing
on OCR accuracy and LLM performance. It compares:

1. Raw processing (no preprocessing)
2. Standard preprocessing (image + text cleaning)
3. Advanced preprocessing (with additional filters)

Run this to validate that preprocessing improves extraction quality.
"""
import io
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image

from api.preprocessing import (
    preprocess_image_for_ocr,
    clean_and_sort_ocr_text,
    preprocess_image_advanced,
    validate_ocr_output
)
from api.extractor import reader, extract_invoice_fields


def process_without_preprocessing(image_bytes: bytes) -> Dict:
    """Process image without any preprocessing (baseline)."""
    start = time.perf_counter()
    
    # Direct OCR without preprocessing
    raw_results = reader.readtext(image_bytes, detail=1, paragraph=False)
    
    # Simple concatenation without sorting or cleaning
    texts = [text for _, text, _ in raw_results]
    raw_text = " ".join(texts)
    
    ocr_time = time.perf_counter() - start
    
    if not raw_text.strip():
        raise ValueError("No text extracted")
    
    # LLM extraction
    llm_start = time.perf_counter()
    result = extract_invoice_fields(raw_text)
    llm_time = time.perf_counter() - llm_start
    
    return {
        'data': result,
        'ocr_time': ocr_time,
        'llm_time': llm_time,
        'total_time': ocr_time + llm_time,
        'text_length': len(raw_text),
        'text_preview': raw_text[:200]
    }


def process_with_standard_preprocessing(image_bytes: bytes) -> Dict:
    """Process image with standard preprocessing pipeline."""
    start = time.perf_counter()
    
    # Image preprocessing
    preprocessed_image = preprocess_image_for_ocr(image_bytes)
    
    # OCR with detail=1 for bounding boxes
    raw_results = reader.readtext(preprocessed_image, detail=1, paragraph=False)
    
    # Text preprocessing (sorting and cleaning)
    clean_text = clean_and_sort_ocr_text(raw_results)
    
    ocr_time = time.perf_counter() - start
    
    if not clean_text.strip():
        raise ValueError("No text extracted")
    
    # LLM extraction
    llm_start = time.perf_counter()
    result = extract_invoice_fields(clean_text)
    llm_time = time.perf_counter() - llm_start
    
    return {
        'data': result,
        'ocr_time': ocr_time,
        'llm_time': llm_time,
        'total_time': ocr_time + llm_time,
        'text_length': len(clean_text),
        'text_preview': clean_text[:200]
    }


def process_with_advanced_preprocessing(image_bytes: bytes) -> Dict:
    """Process image with advanced preprocessing (denoise + sharpen)."""
    start = time.perf_counter()
    
    # Advanced image preprocessing with sharpening
    preprocessed_image = preprocess_image_advanced(
        image_bytes,
        max_dimension=1500,
        denoise=True,
        sharpen=True
    )
    
    # OCR with detail=1 for bounding boxes
    raw_results = reader.readtext(preprocessed_image, detail=1, paragraph=False)
    
    # Text preprocessing (sorting and cleaning)
    clean_text = clean_and_sort_ocr_text(raw_results)
    
    ocr_time = time.perf_counter() - start
    
    if not clean_text.strip():
        raise ValueError("No text extracted")
    
    # LLM extraction
    llm_start = time.perf_counter()
    result = extract_invoice_fields(clean_text)
    llm_time = time.perf_counter() - llm_start
    
    return {
        'data': result,
        'ocr_time': ocr_time,
        'llm_time': llm_time,
        'total_time': ocr_time + llm_time,
        'text_length': len(clean_text),
        'text_preview': clean_text[:200]
    }


def compare_preprocessing_methods(image_path: str) -> None:
    """
    Compare all three preprocessing methods on a single image.
    
    Args:
        image_path: Path to the test invoice image
    """
    print("\n" + "=" * 80)
    print(" PREPROCESSING PIPELINE COMPARISON TEST")
    print("=" * 80)
    print(f"\nTest Image: {image_path}\n")
    
    # Load image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"Original Image Size: {len(image_bytes) / 1024:.2f} KB\n")
    
    methods = [
        ("No Preprocessing (Baseline)", process_without_preprocessing),
        ("Standard Preprocessing", process_with_standard_preprocessing),
        ("Advanced Preprocessing", process_with_advanced_preprocessing)
    ]
    
    results = []
    
    for method_name, method_func in methods:
        print(f"Testing: {method_name}")
        print("-" * 80)
        
        try:
            result = method_func(image_bytes)
            
            print(f"✓ Success")
            print(f"  OCR Time: {result['ocr_time']:.3f}s")
            print(f"  LLM Time: {result['llm_time']:.3f}s")
            print(f"  Total Time: {result['total_time']:.3f}s")
            print(f"  Text Length: {result['text_length']} characters")
            print(f"\n  Extracted Data:")
            for key, value in result['data'].items():
                print(f"    {key}: {value}")
            print(f"\n  Text Preview:\n    {result['text_preview'][:150]}...\n")
            
            results.append((method_name, result))
            
        except Exception as e:
            print(f"✗ Failed: {str(e)}\n")
            results.append((method_name, None))
    
    # Summary comparison
    print("\n" + "=" * 80)
    print(" SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Method':<30} {'Total Time':<15} {'Text Length':<15} {'Fields Extracted'}")
    print("-" * 80)
    
    for method_name, result in results:
        if result:
            fields_extracted = sum(1 for v in result['data'].values() if v is not None)
            print(f"{method_name:<30} {result['total_time']:<15.3f} {result['text_length']:<15} {fields_extracted}/4")
        else:
            print(f"{method_name:<30} {'FAILED':<15} {'N/A':<15} {'0/4'}")
    
    print("=" * 80)
    
    # Analysis
    if all(r[1] for r in results):
        standard = results[1][1]
        baseline = results[0][1]
        
        time_improvement = ((baseline['total_time'] - standard['total_time']) / baseline['total_time']) * 100
        
        print(f"\n📊 Analysis:")
        print(f"  • Standard preprocessing is {abs(time_improvement):.1f}% {'faster' if time_improvement > 0 else 'slower'} than baseline")
        print(f"  • Text is {((baseline['text_length'] - standard['text_length']) / baseline['text_length'] * 100):.1f}% more concise")
        
        baseline_fields = sum(1 for v in baseline['data'].values() if v is not None)
        standard_fields = sum(1 for v in standard['data'].values() if v is not None)
        
        if standard_fields > baseline_fields:
            print(f"  • Preprocessing extracted {standard_fields - baseline_fields} more field(s)")
        elif standard_fields == baseline_fields:
            print(f"  • Both methods extracted the same number of fields")
        else:
            print(f"  • Baseline extracted {baseline_fields - standard_fields} more field(s)")
    
    print("\n✅ Test complete!\n")


def test_preprocessing_on_dataset_sample(num_samples: int = 5) -> None:
    """
    Test preprocessing on multiple samples from the dataset.
    
    Args:
        num_samples: Number of samples to test
    """
    from api.dataset_loader import Voxel51InvoiceDataset
    
    print("\n" + "=" * 80)
    print(" DATASET SAMPLE PREPROCESSING TEST")
    print("=" * 80)
    print(f"\nTesting on {num_samples} random invoice samples\n")
    
    dataset = Voxel51InvoiceDataset()
    dataset.load()
    
    samples = dataset.get_annotated_samples(limit=num_samples)
    
    baseline_success = 0
    standard_success = 0
    baseline_total_time = 0
    standard_total_time = 0
    
    for i, sample in enumerate(samples):
        print(f"\nSample {i+1}/{len(samples)}: {Path(sample['filepath']).name}")
        print("-" * 80)
        
        # Convert PIL Image to bytes
        img = sample['image']
        if isinstance(img, Image.Image):
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
        else:
            img_bytes = img
        
        # Test baseline
        try:
            baseline_result = process_without_preprocessing(img_bytes)
            baseline_success += 1
            baseline_total_time += baseline_result['total_time']
            print(f"  Baseline: ✓ {baseline_result['total_time']:.3f}s")
        except Exception as e:
            print(f"  Baseline: ✗ {str(e)}")
        
        # Test standard preprocessing
        try:
            standard_result = process_with_standard_preprocessing(img_bytes)
            standard_success += 1
            standard_total_time += standard_result['total_time']
            print(f"  Standard: ✓ {standard_result['total_time']:.3f}s")
        except Exception as e:
            print(f"  Standard: ✗ {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    print(" DATASET TEST SUMMARY")
    print("=" * 80)
    print(f"Baseline Success Rate: {baseline_success}/{num_samples} ({baseline_success/num_samples*100:.1f}%)")
    print(f"Standard Success Rate: {standard_success}/{num_samples} ({standard_success/num_samples*100:.1f}%)")
    
    if baseline_success > 0:
        print(f"Baseline Avg Time: {baseline_total_time/baseline_success:.3f}s")
    if standard_success > 0:
        print(f"Standard Avg Time: {standard_total_time/standard_success:.3f}s")
    
    print("=" * 80)
    print("\n✅ Dataset test complete!\n")


def main():
    """Main test runner."""
    import sys
    
    if len(sys.argv) > 1:
        # Test on specific image
        image_path = sys.argv[1]
        if Path(image_path).exists():
            compare_preprocessing_methods(image_path)
        else:
            print(f"Error: Image not found at {image_path}")
    else:
        # Test on dataset samples
        print("\nNo image path provided. Testing on dataset samples...")
        print("Usage: python test_preprocessing.py <path_to_invoice_image>")
        print("       python test_preprocessing.py  (uses dataset samples)\n")
        
        try:
            test_preprocessing_on_dataset_sample(num_samples=5)
        except Exception as e:
            print(f"\n⚠️  Dataset test failed: {str(e)}")
            print("\nTo test on a specific image, run:")
            print("  python test_preprocessing.py path/to/invoice.jpg")


if __name__ == '__main__':
    main()
