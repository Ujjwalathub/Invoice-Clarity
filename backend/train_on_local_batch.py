"""
Process and Evaluate Local Invoice Dataset

This script processes the local batch1_1 dataset (499 images) and evaluates
the OCR + LLM pipeline performance. Since EasyOCR and Llama 3.2 are pre-trained,
we focus on:
1. Batch processing all images
2. Collecting extraction statistics
3. Identifying common failure patterns
4. Optimizing prompts based on results

Usage:
    python train_on_local_batch.py
"""
import json
import time
from pathlib import Path
from typing import Dict, List
import io

from PIL import Image
from api.extractor import process_image_bytes


def process_local_dataset(
    dataset_path: str = r"E:\OCR\Data\batch1\batch1_1",
    output_dir: str = "./local_batch_results",
    num_samples: int = None
) -> List[Dict]:
    """
    Process local invoice images and collect results.
    
    Args:
        dataset_path: Path to the local image directory
        output_dir: Where to save results
        num_samples: Number of images to process (None = all)
    
    Returns:
        List of processing results
    """
    dataset_dir = Path(dataset_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all invoice images
    image_files = sorted(list(dataset_dir.glob("*.jpg")) + list(dataset_dir.glob("*.png")))
    
    if num_samples:
        image_files = image_files[:num_samples]
    
    print("\n" + "=" * 70)
    print(" LOCAL DATASET PROCESSING")
    print("=" * 70)
    print(f"\nDataset: {dataset_path}")
    print(f"Total images found: {len(image_files)}")
    print(f"Processing: {len(image_files)} images")
    print(f"Output directory: {output_path}\n")
    
    results = []
    successful = 0
    failed = 0
    total_time = 0
    field_stats = {
        'vendor_name': 0,
        'invoice_number': 0,
        'date': 0,
        'total_amount': 0
    }
    
    print("Starting processing...")
    print("-" * 70)
    
    for i, img_path in enumerate(image_files, 1):
        print(f"\rProcessing {i}/{len(image_files)}: {img_path.name}", end="", flush=True)
        
        try:
            # Load image
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            
            # Process through pipeline
            start = time.perf_counter()
            result = process_image_bytes(image_bytes)
            elapsed = time.perf_counter() - start
            
            # Track statistics
            extracted_data = result['data']
            for field in field_stats:
                if extracted_data.get(field) is not None:
                    field_stats[field] += 1
            
            results.append({
                'filename': img_path.name,
                'filepath': str(img_path),
                'status': 'success',
                'extracted_data': extracted_data,
                'processing_time': elapsed,
                'error': None
            })
            
            successful += 1
            total_time += elapsed
            
        except Exception as e:
            results.append({
                'filename': img_path.name,
                'filepath': str(img_path),
                'status': 'failed',
                'extracted_data': {},
                'processing_time': 0,
                'error': str(e)
            })
            failed += 1
    
    print("\n" + "-" * 70)
    print("\n" + "=" * 70)
    print(" PROCESSING COMPLETE")
    print("=" * 70)
    
    # Print summary statistics
    print(f"\nTotal Processed: {len(results)}")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"Success Rate: {successful/len(results)*100:.1f}%")
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"\nPerformance:")
        print(f"  Average Time: {avg_time:.3f}s per invoice")
        print(f"  Throughput: {3600/avg_time:.0f} invoices/hour")
        print(f"  Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    
    print(f"\nField Extraction Rates:")
    for field, count in field_stats.items():
        rate = count / successful * 100 if successful > 0 else 0
        print(f"  {field:20s}: {count:4d}/{successful:4d} ({rate:5.1f}%)")
    
    # Save detailed results
    results_file = output_path / 'processing_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed,
                'success_rate': successful/len(results)*100,
                'avg_processing_time': total_time/successful if successful > 0 else 0,
                'throughput_per_hour': 3600/(total_time/successful) if successful > 0 else 0,
                'field_stats': field_stats
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Detailed results saved to: {results_file}")
    
    # Save CSV for easy analysis
    save_csv(results, output_path / 'processing_results.csv')
    
    # Analyze failures
    if failed > 0:
        analyze_failures(results, output_path)
    
    return results


def save_csv(results: List[Dict], csv_path: Path):
    """Save results to CSV format."""
    import csv
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Filename',
            'Status',
            'Vendor Name',
            'Invoice Number',
            'Date',
            'Total Amount',
            'Processing Time (s)',
            'Error'
        ])
        
        # Data rows
        for result in results:
            data = result.get('extracted_data', {})
            writer.writerow([
                result['filename'],
                result['status'],
                data.get('vendor_name', ''),
                data.get('invoice_number', ''),
                data.get('date', ''),
                data.get('total_amount', ''),
                f"{result['processing_time']:.3f}",
                result.get('error', '')
            ])
    
    print(f"✓ CSV exported to: {csv_path}")


def analyze_failures(results: List[Dict], output_path: Path):
    """Analyze and report on failures."""
    failures = [r for r in results if r['status'] == 'failed']
    
    failure_file = output_path / 'failures.txt'
    with open(failure_file, 'w', encoding='utf-8') as f:
        f.write("FAILURE ANALYSIS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total Failures: {len(failures)}\n\n")
        
        # Group by error type
        error_types = {}
        for failure in failures:
            error = failure.get('error', 'Unknown')
            error_types[error] = error_types.get(error, 0) + 1
        
        f.write("Error Types:\n")
        f.write("-" * 70 + "\n")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{count:4d}x {error}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("Detailed Failure List:\n")
        f.write("-" * 70 + "\n")
        for failure in failures:
            f.write(f"\nFile: {failure['filename']}\n")
            f.write(f"Error: {failure['error']}\n")
    
    print(f"✓ Failure analysis saved to: {failure_file}")


def main():
    """Main execution function."""
    import sys
    
    # Default parameters
    dataset_path = r"E:\OCR\Data\batch1\batch1_1"
    num_samples = None  # Process all images
    
    # Check if custom parameters provided
    if len(sys.argv) > 1:
        num_samples = int(sys.argv[1])
        print(f"\nProcessing first {num_samples} images only...")
    
    # Check if dataset exists
    if not Path(dataset_path).exists():
        print(f"\n✗ Error: Dataset not found at {dataset_path}")
        print("\nPlease verify the path and try again.")
        return
    
    # Process dataset
    try:
        results = process_local_dataset(
            dataset_path=dataset_path,
            num_samples=num_samples
        )
        
        print("\n" + "=" * 70)
        print(" NEXT STEPS")
        print("=" * 70)
        print("\n1. Review the results:")
        print("   - processing_results.json (detailed JSON)")
        print("   - processing_results.csv (Excel-friendly)")
        print("   - failures.txt (error analysis)")
        
        print("\n2. Analyze extraction patterns:")
        print("   - Which fields have low extraction rates?")
        print("   - What types of invoices fail most?")
        
        print("\n3. Optimize the system:")
        print("   - Tune SYSTEM_PROMPT in api/extractor.py")
        print("   - Adjust preprocessing parameters")
        print("   - Add field-specific validation")
        
        print("\n4. Process remaining batches:")
        print("   - batch1_2 (501 images)")
        print("   - batch1_3 (489 images)")
        
        print("\n5. Start the API for manual testing:")
        print("   uvicorn api.main:app --port 8000")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Processing interrupted by user")
        print("Partial results may be available in ./local_batch_results/")
    except Exception as e:
        print(f"\n\n✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
