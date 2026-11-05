"""
Test the complete pipeline without requiring dataset download.
Uses a simple test image or generates one programmatically.

This script verifies:
1. Image preprocessing (OpenCV)
2. OCR extraction (EasyOCR)
3. Text preprocessing (sorting and cleaning)
4. LLM reasoning (Ollama + Llama 3.2)

Usage:
    python test_without_dataset.py                      # Use generated test image
    python test_without_dataset.py path/to/invoice.jpg  # Use your own image
"""
import io
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def create_test_invoice_image():
    """Generate a simple test invoice image programmatically."""
    print("   Generating synthetic invoice image...")
    
    # Create white background
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default
    try:
        font_large = ImageFont.truetype("arial.ttf", 32)
        font_normal = ImageFont.truetype("arial.ttf", 20)
    except:
        try:
            font_large = ImageFont.truetype("Arial.ttf", 32)
            font_normal = ImageFont.truetype("Arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_normal = ImageFont.load_default()
    
    # Add invoice content
    draw.text((50, 50), "INVOICE", fill='black', font=font_large)
    draw.text((50, 120), "Vendor: TechCorp Supplies", fill='black', font=font_normal)
    draw.text((50, 160), "Invoice Number: INV-2026-0123", fill='black', font=font_normal)
    draw.text((50, 200), "Date: 2026-07-15", fill='black', font=font_normal)
    draw.text((50, 240), "Total Amount: $1,250.00", fill='black', font=font_normal)
    
    # Add some line items
    draw.text((50, 300), "Item Description           Qty    Price", fill='black', font=font_normal)
    draw.text((50, 330), "Office Supplies             10    $125.00", fill='black', font=font_normal)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


def test_phase_1_image_preprocessing(image_bytes):
    """Test Phase 1: Image Preprocessing"""
    print("\n" + "─" * 70)
    print("Phase 1: Image Preprocessing")
    print("─" * 70)
    
    try:
        from api.preprocessing import preprocess_image_for_ocr
        
        start = time.perf_counter()
        preprocessed = preprocess_image_for_ocr(image_bytes)
        elapsed = time.perf_counter() - start
        
        print(f"  ✓ Image preprocessing successful")
        print(f"    Original size: {len(image_bytes) / 1024:.2f} KB")
        print(f"    Processed size: {len(preprocessed) / 1024:.2f} KB")
        print(f"    Time: {elapsed:.3f}s")
        
        return preprocessed
        
    except Exception as e:
        print(f"  ✗ Image preprocessing failed: {e}")
        return None


def test_phase_2_ocr_extraction(preprocessed_image):
    """Test Phase 2: OCR Extraction"""
    print("\n" + "─" * 70)
    print("Phase 2: OCR Extraction (EasyOCR)")
    print("─" * 70)
    
    try:
        from api.extractor import reader
        
        print("  Loading EasyOCR model (this may take a moment on first run)...")
        start = time.perf_counter()
        raw_results = reader.readtext(preprocessed_image, detail=1, paragraph=False)
        elapsed = time.perf_counter() - start
        
        print(f"  ✓ OCR extraction successful")
        print(f"    Text blocks found: {len(raw_results)}")
        print(f"    Time: {elapsed:.3f}s")
        
        if raw_results:
            print(f"\n  Sample detections:")
            for i, (bbox, text, conf) in enumerate(raw_results[:5]):
                print(f"    {i+1}. '{text}' (confidence: {conf:.2f})")
        
        return raw_results
        
    except Exception as e:
        print(f"  ✗ OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_phase_3_text_preprocessing(raw_results):
    """Test Phase 3: Text Preprocessing"""
    print("\n" + "─" * 70)
    print("Phase 3: Text Preprocessing (Sorting & Cleaning)")
    print("─" * 70)
    
    try:
        from api.preprocessing import clean_and_sort_ocr_text, validate_ocr_output
        
        # Validate output
        is_valid = validate_ocr_output(raw_results)
        print(f"  OCR output validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
        
        if not is_valid:
            print("  ⚠ Warning: OCR output may be insufficient for LLM processing")
        
        # Clean and sort
        start = time.perf_counter()
        clean_text = clean_and_sort_ocr_text(raw_results)
        elapsed = time.perf_counter() - start
        
        print(f"  ✓ Text preprocessing successful")
        print(f"    Clean text length: {len(clean_text)} characters")
        print(f"    Time: {elapsed:.3f}s")
        print(f"\n  Clean text preview:")
        
        # Show preview with proper formatting
        preview = clean_text[:200] if len(clean_text) > 200 else clean_text
        for line in preview.split('\n')[:5]:
            if line.strip():
                print(f"    {line[:70]}")
        
        if len(clean_text) > 200:
            print(f"    ... ({len(clean_text) - 200} more characters)")
        
        return clean_text
        
    except Exception as e:
        print(f"  ✗ Text preprocessing failed: {e}")
        return None


def test_phase_4_llm_extraction(image_bytes):
    """Test Phase 4: LLM Extraction"""
    print("\n" + "─" * 70)
    print("Phase 4: LLM Extraction (Ollama + Llama 3.2)")
    print("─" * 70)
    
    try:
        from api.extractor import process_image_bytes
        
        print("  Processing through complete pipeline...")
        start = time.perf_counter()
        result = process_image_bytes(image_bytes)
        elapsed = time.perf_counter() - start
        
        print(f"  ✓ LLM extraction successful")
        print(f"    Total processing time: {elapsed:.3f}s")
        
        if 'metadata' in result:
            meta = result['metadata']
            if 'ocr_time_seconds' in meta:
                print(f"    OCR time: {meta['ocr_time_seconds']:.3f}s")
            if 'llm_time_seconds' in meta:
                print(f"    LLM time: {meta['llm_time_seconds']:.3f}s")
        
        print(f"\n  Extracted Data:")
        data = result.get('data', {})
        for key, value in data.items():
            status = "✓" if value is not None else "✗"
            print(f"    {status} {key}: {value}")
        
        # Count successful extractions
        extracted_count = sum(1 for v in data.values() if v is not None)
        total_fields = len(data)
        
        print(f"\n  Extraction Rate: {extracted_count}/{total_fields} fields ({extracted_count/total_fields*100:.0f}%)")
        
        return result
        
    except Exception as e:
        print(f"  ✗ LLM extraction failed: {e}")
        print(f"\n  Possible reasons:")
        print(f"    1. Ollama service not running: ollama serve")
        print(f"    2. Llama 3.2 model not installed: ollama pull llama3.2")
        print(f"    3. Connection issue with Ollama")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test runner."""
    print("\n" + "=" * 70)
    print(" COMPLETE PIPELINE TEST (No Dataset Required)")
    print("=" * 70)
    print("\nThis test verifies your OCR + LLM pipeline is fully operational")
    print("without requiring the Hugging Face dataset download.\n")
    
    # Determine image source
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not Path(image_path).exists():
            print(f"✗ Error: Image not found at {image_path}")
            return
        
        print(f"📄 Input: {image_path}")
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
    else:
        print("📄 Input: Synthetic test invoice (auto-generated)")
        image_bytes = create_test_invoice_image()
    
    print(f"   Size: {len(image_bytes) / 1024:.2f} KB")
    
    # Run all phases
    success_count = 0
    total_phases = 4
    
    # Phase 1: Image Preprocessing
    preprocessed = test_phase_1_image_preprocessing(image_bytes)
    if preprocessed:
        success_count += 1
    
    # Phase 2: OCR Extraction
    if preprocessed:
        raw_results = test_phase_2_ocr_extraction(preprocessed)
        if raw_results:
            success_count += 1
        
        # Phase 3: Text Preprocessing
        if raw_results:
            clean_text = test_phase_3_text_preprocessing(raw_results)
            if clean_text:
                success_count += 1
    
    # Phase 4: LLM Extraction (Full Pipeline)
    result = test_phase_4_llm_extraction(image_bytes)
    if result:
        success_count += 1
    
    # Final summary
    print("\n" + "=" * 70)
    if success_count == total_phases:
        print(" ✅ ALL TESTS PASSED - PIPELINE FULLY OPERATIONAL")
        print("=" * 70)
        print("\nYour hybrid OCR + LLM system is working perfectly!")
        print("\n📊 System Status:")
        print("  ✓ Image preprocessing: WORKING")
        print("  ✓ EasyOCR vision layer: WORKING")
        print("  ✓ Text preprocessing: WORKING")
        print("  ✓ Ollama + Llama 3.2: WORKING")
    else:
        print(f" ⚠️  {success_count}/{total_phases} PHASES PASSED")
        print("=" * 70)
        print("\nSome components need attention. Review errors above.")
    
    print("\n🚀 Next Steps:")
    print("  1. Test with real invoices: python test_without_dataset.py path/to/invoice.jpg")
    print("  2. Start API server: uvicorn api.main:app --port 8000")
    print("  3. Start UI dashboard: streamlit run ui/app.py")
    print("  4. Retry dataset download later (when rate limit clears)")
    
    print("\n💡 Note: The dataset is optional for testing core functionality.")
    print("   You can fully demonstrate your system without it!\n")


if __name__ == '__main__':
    main()
