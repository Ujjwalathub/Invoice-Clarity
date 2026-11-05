"""
Single Invoice Testing Script

Test your pipeline on a single invoice from the dataset and see
the complete extraction process with detailed output.

Perfect for debugging and demonstrating the pipeline during the hackathon.
"""
import json
import sys
from pathlib import Path

from PIL import Image

from api.dataset_loader import Voxel51InvoiceDataset
from api.extractor import process_image_bytes


def print_invoice_result(result: dict, ground_truth: dict = None):
    """Print formatted extraction results."""
    print("\n" + "=" * 70)
    print(" EXTRACTION RESULTS")
    print("=" * 70)
    
    data = result['data']
    
    print("\n📄 Extracted Fields:")
    print("─" * 70)
    print(f"  Vendor Name:     {data.get('vendor_name') or 'NULL'}")
    print(f"  Invoice Number:  {data.get('invoice_number') or 'NULL'}")
    print(f"  Date:            {data.get('date') or 'NULL'}")
    print(f"  Total Amount:    {data.get('total_amount') or 'NULL'}")
    print("─" * 70)
    
    print(f"\n⏱️  Processing Time: {result['metadata']['processing_time_seconds']:.3f} seconds")
    
    # Compare with ground truth if available
    if ground_truth:
        print("\n" + "=" * 70)
        print(" GROUND TRUTH COMPARISON")
        print("=" * 70)
        
        fields = ['vendor_name', 'invoice_number', 'date', 'total_amount']
        
        all_correct = True
        for field in fields:
            extracted = str(data.get(field) or '').strip().lower()
            truth = str(ground_truth.get(field) or '').strip().lower()
            
            is_correct = extracted == truth
            status = "✓" if is_correct else "✗"
            
            print(f"\n  {field}:")
            print(f"    Extracted:    {data.get(field) or 'NULL'}")
            print(f"    Ground Truth: {ground_truth.get(field) or 'NULL'}")
            print(f"    Status:       {status} {'CORRECT' if is_correct else 'INCORRECT'}")
            
            if not is_correct:
                all_correct = False
        
        print("\n" + "─" * 70)
        if all_correct:
            print("  ✅ ALL FIELDS MATCH GROUND TRUTH!")
        else:
            print("  ⚠️  Some fields do not match. Review extraction logic.")
        print("─" * 70)


def test_random_invoice():
    """Test on a random invoice from the dataset."""
    print("\n" + "=" * 70)
    print(" RANDOM INVOICE TEST")
    print("=" * 70)
    
    print("\nLoading dataset...")
    dataset = Voxel51InvoiceDataset()
    dataset.load()
    
    # Pick a random sample
    import random
    samples = dataset.get_annotated_samples(limit=100)
    sample = random.choice(samples)
    
    print(f"\nSelected: {sample['filepath']}")
    print("Processing invoice through pipeline...\n")
    
    # Convert PIL Image to bytes
    img = sample['image']
    if isinstance(img, Image.Image):
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
    else:
        img_bytes = img
    
    # Process
    try:
        result = process_image_bytes(img_bytes)
        print_invoice_result(result, sample['ground_truth'])
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


def test_specific_invoice(index: int):
    """
    Test on a specific invoice by index.
    
    Args:
        index: Index of the invoice in the dataset (0-1488)
    """
    print("\n" + "=" * 70)
    print(f" TESTING INVOICE #{index}")
    print("=" * 70)
    
    print("\nLoading dataset...")
    dataset = Voxel51InvoiceDataset()
    dataset.load()
    
    try:
        sample = dataset.get_sample(index, split='train')
    except IndexError:
        print(f"\n❌ Invalid index. Please use 0-1488 for annotated samples.")
        return
    
    print(f"\nSelected: {sample['filepath']}")
    print("Processing invoice through pipeline...\n")
    
    # Convert PIL Image to bytes
    img = sample['image']
    if isinstance(img, Image.Image):
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
    else:
        img_bytes = img
    
    # Process
    try:
        result = process_image_bytes(img_bytes)
        print_invoice_result(result, sample['ground_truth'])
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


def test_local_image(image_path: str):
    """
    Test on a local image file.
    
    Args:
        image_path: Path to a local invoice image (JPG/PNG)
    """
    print("\n" + "=" * 70)
    print(f" TESTING LOCAL IMAGE")
    print("=" * 70)
    
    if not Path(image_path).exists():
        print(f"\n❌ File not found: {image_path}")
        return
    
    print(f"\nImage: {image_path}")
    print("Processing invoice through pipeline...\n")
    
    # Read image
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    
    # Process
    try:
        result = process_image_bytes(img_bytes)
        print_invoice_result(result)
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


def interactive_mode():
    """Interactive testing interface."""
    print("\n" + "=" * 70)
    print(" INTERACTIVE INVOICE TESTING")
    print("=" * 70)
    
    print("\nOptions:")
    print("  1. Test random invoice from dataset")
    print("  2. Test specific invoice by index (0-1488)")
    print("  3. Test local image file")
    print("  4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            test_random_invoice()
            
        elif choice == '2':
            try:
                index = int(input("Enter invoice index (0-1488): ").strip())
                test_specific_invoice(index)
            except ValueError:
                print("❌ Invalid index. Please enter a number.")
            
        elif choice == '3':
            image_path = input("Enter path to image file: ").strip()
            test_local_image(image_path)
            
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-4.")


def main():
    """Main entry point with command-line argument support."""
    if len(sys.argv) == 1:
        # No arguments - run interactive mode
        interactive_mode()
        
    elif sys.argv[1] == 'random':
        # Test random invoice
        test_random_invoice()
        
    elif sys.argv[1] == 'index':
        # Test specific index
        if len(sys.argv) < 3:
            print("❌ Usage: python test_single_invoice.py index <INDEX>")
            return
        
        try:
            index = int(sys.argv[2])
            test_specific_invoice(index)
        except ValueError:
            print("❌ Invalid index. Please provide a number.")
    
    elif sys.argv[1] == 'local':
        # Test local file
        if len(sys.argv) < 3:
            print("❌ Usage: python test_single_invoice.py local <IMAGE_PATH>")
            return
        
        test_local_image(sys.argv[2])
    
    else:
        print("❌ Invalid command.")
        print("\nUsage:")
        print("  python test_single_invoice.py              # Interactive mode")
        print("  python test_single_invoice.py random       # Test random invoice")
        print("  python test_single_invoice.py index <N>    # Test invoice at index N")
        print("  python test_single_invoice.py local <PATH> # Test local image file")


if __name__ == '__main__':
    main()
