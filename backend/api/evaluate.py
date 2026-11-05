"""
Evaluation script for the invoice extraction pipeline.

This script:
1. Loads the annotated Voxel51 dataset (Batch 1)
2. Runs your EasyOCR + Llama 3.2 pipeline on each image
3. Compares extracted JSON against ground truth
4. Generates accuracy metrics and error analysis
"""
import json
import time
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

from .dataset_loader import Voxel51InvoiceDataset
from .extractor import process_image_bytes


class InvoiceEvaluator:
    """Evaluates invoice extraction accuracy against ground truth."""
    
    def __init__(self):
        self.dataset = Voxel51InvoiceDataset()
        self.results = []
    
    def normalize_value(self, value) -> str:
        """Normalize a field value for comparison."""
        if value is None:
            return ""
        return str(value).strip().lower()
    
    def compare_fields(self, predicted: Dict, ground_truth: Dict) -> Dict[str, bool]:
        """
        Compare predicted fields against ground truth.
        
        Returns:
            Dictionary mapping field names to correctness (True/False)
        """
        fields = ['vendor_name', 'invoice_number', 'date', 'total_amount']
        comparison = {}
        
        for field in fields:
            pred_val = self.normalize_value(predicted.get(field))
            gt_val = self.normalize_value(ground_truth.get(field))
            
            # Exact match comparison
            comparison[field] = pred_val == gt_val
        
        return comparison
    
    def evaluate_sample(self, sample: Dict) -> Dict:
        """
        Process a single sample and evaluate accuracy.
        
        Args:
            sample: Dictionary with 'image' and 'ground_truth'
        
        Returns:
            Dictionary containing predictions, ground truth, and comparison
        """
        # Convert PIL Image to bytes
        img = sample['image']
        if isinstance(img, Image.Image):
            import io
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
        else:
            img_bytes = img
        
        # Run extraction pipeline
        try:
            result = process_image_bytes(img_bytes)
            predicted = result['data']
            processing_time = result['metadata']['processing_time_seconds']
            error = None
        except Exception as e:
            predicted = {}
            processing_time = 0
            error = str(e)
        
        ground_truth = sample['ground_truth']
        
        # Compare fields
        comparison = self.compare_fields(predicted, ground_truth)
        
        return {
            'filepath': sample['filepath'],
            'predicted': predicted,
            'ground_truth': ground_truth,
            'comparison': comparison,
            'processing_time': processing_time,
            'error': error
        }
    
    def run_evaluation(self, num_samples: int = 100, start_idx: int = 0) -> Dict:
        """
        Run evaluation on multiple samples.
        
        Args:
            num_samples: Number of samples to evaluate
            start_idx: Starting index in the dataset
        
        Returns:
            Dictionary containing overall metrics and per-sample results
        """
        print(f"Loading dataset and preparing {num_samples} samples...")
        self.dataset.load()
        
        samples = self.dataset.get_annotated_samples(limit=start_idx + num_samples)
        samples = samples[start_idx:start_idx + num_samples]
        
        print(f"Running evaluation on {len(samples)} samples...")
        print("This may take several minutes depending on your hardware.\n")
        
        self.results = []
        field_correct_counts = {
            'vendor_name': 0,
            'invoice_number': 0,
            'date': 0,
            'total_amount': 0
        }
        total_processing_time = 0
        errors = 0
        
        for i, sample in enumerate(samples):
            print(f"Processing sample {i+1}/{len(samples)}...", end='\r')
            
            result = self.evaluate_sample(sample)
            self.results.append(result)
            
            if result['error']:
                errors += 1
            else:
                # Update accuracy counts
                for field, is_correct in result['comparison'].items():
                    if is_correct:
                        field_correct_counts[field] += 1
                
                total_processing_time += result['processing_time']
        
        print("\n")
        
        # Calculate metrics
        total_evaluated = len(samples) - errors
        field_accuracies = {
            field: (count / total_evaluated * 100 if total_evaluated > 0 else 0)
            for field, count in field_correct_counts.items()
        }
        
        overall_accuracy = sum(field_accuracies.values()) / len(field_accuracies)
        avg_processing_time = total_processing_time / total_evaluated if total_evaluated > 0 else 0
        
        return {
            'summary': {
                'total_samples': len(samples),
                'successful': total_evaluated,
                'errors': errors,
                'overall_accuracy': round(overall_accuracy, 2),
                'field_accuracies': {k: round(v, 2) for k, v in field_accuracies.items()},
                'avg_processing_time_seconds': round(avg_processing_time, 3)
            },
            'per_sample_results': self.results
        }
    
    def print_report(self, metrics: Dict) -> None:
        """Print a formatted evaluation report."""
        summary = metrics['summary']
        
        print("=" * 70)
        print(" INVOICE EXTRACTION EVALUATION REPORT")
        print("=" * 70)
        print(f"\nDataset: Voxel51 High-Quality Invoice Images (Batch 1)")
        print(f"Total Samples: {summary['total_samples']}")
        print(f"Successful Extractions: {summary['successful']}")
        print(f"Errors: {summary['errors']}")
        print(f"\nOVERALL ACCURACY: {summary['overall_accuracy']:.2f}%")
        print("\nFIELD-LEVEL ACCURACY:")
        print("-" * 70)
        
        for field, accuracy in summary['field_accuracies'].items():
            bar_length = int(accuracy / 2)  # Scale to 50 chars max
            bar = "█" * bar_length + "░" * (50 - bar_length)
            print(f"  {field:20s} │ {bar} │ {accuracy:6.2f}%")
        
        print("-" * 70)
        print(f"\nAverage Processing Time: {summary['avg_processing_time_seconds']:.3f} seconds per invoice")
        print("=" * 70)
    
    def export_results(self, output_path: str, metrics: Dict) -> None:
        """Export evaluation results to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n✓ Detailed results exported to: {output_path}")
    
    def find_errors(self, metrics: Dict, max_display: int = 5) -> None:
        """Display examples of incorrect extractions for debugging."""
        print("\n" + "=" * 70)
        print(" ERROR ANALYSIS - Incorrect Extractions")
        print("=" * 70)
        
        errors_found = 0
        
        for result in metrics['per_sample_results']:
            if result['error']:
                continue
            
            # Find any incorrect fields
            incorrect_fields = [
                field for field, is_correct in result['comparison'].items()
                if not is_correct
            ]
            
            if incorrect_fields and errors_found < max_display:
                errors_found += 1
                print(f"\nSample: {result['filepath']}")
                print("-" * 70)
                
                for field in incorrect_fields:
                    predicted = result['predicted'].get(field, 'NULL')
                    ground_truth = result['ground_truth'].get(field, 'NULL')
                    print(f"  {field}:")
                    print(f"    Predicted:    {predicted}")
                    print(f"    Ground Truth: {ground_truth}")
        
        if errors_found == 0:
            print("\n✓ No errors found in the evaluated samples!")
        else:
            print("\n" + "=" * 70)


def run_evaluation_demo(num_samples: int = 50):
    """
    Run a demonstration evaluation on the Voxel51 dataset.
    
    Args:
        num_samples: Number of samples to evaluate (default: 50)
    """
    evaluator = InvoiceEvaluator()
    
    print("\n🚀 Starting Invoice Extraction Evaluation")
    print(f"   Target: {num_samples} samples from Voxel51 dataset\n")
    
    start_time = time.time()
    metrics = evaluator.run_evaluation(num_samples=num_samples)
    total_time = time.time() - start_time
    
    # Print results
    evaluator.print_report(metrics)
    evaluator.find_errors(metrics, max_display=3)
    
    # Export results
    evaluator.export_results('evaluation_results.json', metrics)
    
    print(f"\n⏱️  Total Evaluation Time: {total_time:.1f} seconds")
    print("\n✅ Evaluation complete!")


if __name__ == '__main__':
    # Run evaluation on 50 samples by default
    # Adjust this number based on your time constraints
    run_evaluation_demo(num_samples=50)
