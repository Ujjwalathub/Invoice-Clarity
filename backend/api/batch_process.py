"""
Batch Processing Script for Unannotated Invoice Images

This script processes the 6,692 unannotated images from Batches 2 & 3
to demonstrate scalability and real-world application of your pipeline.

Perfect for showing judges at TechEx Amsterdam that your solution
works on fresh, never-seen-before data.
"""
import json
import time
from pathlib import Path
from typing import Dict, List

from PIL import Image

from .dataset_loader import Voxel51InvoiceDataset
from .extractor import process_image_bytes


class BatchProcessor:
    """Process multiple invoices and export results."""
    
    def __init__(self, output_dir: str = './batch_results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataset = Voxel51InvoiceDataset()
        self.results = []
    
    def process_unannotated_batch(
        self,
        num_samples: int = 100,
        start_idx: int = 0,
        save_interval: int = 10
    ) -> List[Dict]:
        """
        Process a batch of unannotated invoice images.
        
        Args:
            num_samples: Number of images to process
            start_idx: Starting index in the unannotated dataset
            save_interval: Save results every N samples (for crash recovery)
        
        Returns:
            List of dictionaries containing filepath and extracted data
        """
        print(f"Loading unannotated invoice images...")
        self.dataset.load()
        
        samples = self.dataset.get_unannotated_samples(limit=start_idx + num_samples)
        
        if not samples:
            print("⚠️  No unannotated samples found in the dataset.")
            print("   The dataset may only contain annotated training data.")
            print("   Try processing annotated samples instead.")
            return []
        
        samples = samples[start_idx:start_idx + num_samples]
        
        print(f"\n🚀 Starting batch processing of {len(samples)} invoices...")
        print(f"   Results will be saved to: {self.output_dir}\n")
        
        self.results = []
        successful = 0
        errors = 0
        total_time = 0
        
        for i, sample in enumerate(samples):
            print(f"Processing {i+1}/{len(samples)}: {sample['filepath'][:50]}...", end='\r')
            
            # Convert PIL Image to bytes
            img = sample['image']
            if isinstance(img, Image.Image):
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
            else:
                img_bytes = img
            
            # Process image
            try:
                result = process_image_bytes(img_bytes)
                extracted = result['data']
                processing_time = result['metadata']['processing_time_seconds']
                error = None
                successful += 1
                total_time += processing_time
            except Exception as e:
                extracted = {}
                processing_time = 0
                error = str(e)
                errors += 1
            
            self.results.append({
                'filepath': sample['filepath'],
                'extracted_data': extracted,
                'processing_time_seconds': processing_time,
                'error': error
            })
            
            # Periodic save for crash recovery
            if (i + 1) % save_interval == 0:
                self._save_checkpoint(start_idx + i + 1)
        
        print("\n")
        
        # Print summary
        print("=" * 70)
        print(" BATCH PROCESSING COMPLETE")
        print("=" * 70)
        print(f"Total Processed: {len(samples)}")
        print(f"Successful: {successful}")
        print(f"Errors: {errors}")
        
        if successful > 0:
            avg_time = total_time / successful
            print(f"Average Processing Time: {avg_time:.3f} seconds per invoice")
            print(f"Estimated Total Time for 6,692 images: {(avg_time * 6692 / 3600):.1f} hours")
        
        print("=" * 70)
        
        return self.results
    
    def _save_checkpoint(self, processed_count: int) -> None:
        """Save intermediate results."""
        checkpoint_file = self.output_dir / f'checkpoint_{processed_count}.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def export_results(self, filename: str = 'batch_results.json') -> None:
        """Export final results to JSON file."""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump({
                'total_processed': len(self.results),
                'successful': len([r for r in self.results if r['error'] is None]),
                'errors': len([r for r in self.results if r['error'] is not None]),
                'results': self.results
            }, f, indent=2)
        
        print(f"\n✓ Results exported to: {output_file}")
    
    def export_csv(self, filename: str = 'batch_results.csv') -> None:
        """Export results to CSV format for easy analysis."""
        import csv
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Filepath',
                'Vendor Name',
                'Invoice Number',
                'Date',
                'Total Amount',
                'Processing Time (s)',
                'Error'
            ])
            
            # Data rows
            for result in self.results:
                data = result['extracted_data']
                writer.writerow([
                    result['filepath'],
                    data.get('vendor_name', ''),
                    data.get('invoice_number', ''),
                    data.get('date', ''),
                    data.get('total_amount', ''),
                    result['processing_time_seconds'],
                    result['error'] or ''
                ])
        
        print(f"✓ CSV exported to: {output_file}")
    
    def process_annotated_demo(self, num_samples: int = 20) -> None:
        """
        Process annotated samples as a demonstration (with known ground truth).
        
        Useful for showing the pipeline working correctly before scaling
        to the full unannotated dataset.
        """
        print(f"Loading annotated invoice images...")
        self.dataset.load()
        
        samples = self.dataset.get_annotated_samples(limit=num_samples)
        
        print(f"\n🚀 Processing {len(samples)} annotated invoices...")
        print(f"   (Ground truth available for verification)\n")
        
        self.results = []
        
        for i, sample in enumerate(samples):
            print(f"Processing {i+1}/{len(samples)}...", end='\r')
            
            # Convert PIL Image to bytes
            img = sample['image']
            if isinstance(img, Image.Image):
                import io
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
            else:
                img_bytes = img
            
            try:
                result = process_image_bytes(img_bytes)
                extracted = result['data']
                processing_time = result['metadata']['processing_time_seconds']
                error = None
            except Exception as e:
                extracted = {}
                processing_time = 0
                error = str(e)
            
            self.results.append({
                'filepath': sample['filepath'],
                'extracted_data': extracted,
                'ground_truth': sample['ground_truth'],
                'processing_time_seconds': processing_time,
                'error': error
            })
        
        print("\n")
        self.export_results('annotated_demo_results.json')


def run_batch_demo(num_samples: int = 100):
    """
    Demo function to batch process invoices.
    
    Args:
        num_samples: Number of invoices to process (default: 100)
    """
    processor = BatchProcessor()
    
    print("\n" + "=" * 70)
    print(" BATCH INVOICE PROCESSING DEMO")
    print("=" * 70)
    print(f"\nTarget: Process {num_samples} invoices from Voxel51 dataset")
    print("This demonstrates your pipeline's scalability for the hackathon.\n")
    
    start_time = time.time()
    
    # Try unannotated first, fall back to annotated if unavailable
    results = processor.process_unannotated_batch(num_samples=num_samples)
    
    if not results:
        print("\nFalling back to annotated samples for demonstration...")
        processor.process_annotated_demo(num_samples=num_samples)
    
    total_time = time.time() - start_time
    
    # Export results
    processor.export_results()
    processor.export_csv()
    
    print(f"\n⏱️  Total Execution Time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print("\n✅ Batch processing complete!")
    print("\nNext steps for the hackathon:")
    print("  1. Review batch_results.json and batch_results.csv")
    print("  2. Analyze extraction accuracy and identify patterns")
    print("  3. Iterate on your prompt engineering in extractor.py")
    print("  4. Scale up to process all 6,692 unannotated images")


if __name__ == '__main__':
    # Process 100 invoices as a demo
    # Adjust this number based on your time and compute resources
    run_batch_demo(num_samples=100)
