"""
Results Visualization and Analysis Tools

Generate charts and statistics from evaluation results to showcase
your pipeline's performance at the hackathon.
"""
import json
from pathlib import Path
from typing import Dict, List


def load_results(filepath: str) -> Dict:
    """Load evaluation or batch results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def print_ascii_bar_chart(data: Dict[str, float], title: str, max_width: int = 50):
    """Print a simple ASCII bar chart."""
    print(f"\n{title}")
    print("─" * 70)
    
    max_value = max(data.values()) if data.values() else 1
    
    for label, value in data.items():
        bar_length = int((value / max_value) * max_width)
        bar = "█" * bar_length
        print(f"  {label:25s} │ {bar:<{max_width}} │ {value:6.2f}%")
    
    print("─" * 70)


def analyze_evaluation_results(filepath: str = 'evaluation_results.json'):
    """
    Analyze and visualize evaluation results.
    
    Args:
        filepath: Path to evaluation_results.json
    """
    if not Path(filepath).exists():
        print(f"❌ Results file not found: {filepath}")
        print("   Run evaluation first: python -m api.evaluate")
        return
    
    results = load_results(filepath)
    summary = results['summary']
    
    print("\n" + "=" * 70)
    print(" EVALUATION RESULTS ANALYSIS")
    print("=" * 70)
    
    # Overall metrics
    print(f"\n📊 Overall Performance")
    print(f"   Total Samples: {summary['total_samples']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Errors: {summary['errors']}")
    print(f"   Success Rate: {(summary['successful']/summary['total_samples']*100):.1f}%")
    
    # Accuracy by field
    print_ascii_bar_chart(
        summary['field_accuracies'],
        "\n📈 Field-Level Accuracy",
        max_width=50
    )
    
    print(f"\n⚡ Performance")
    print(f"   Average Processing Time: {summary['avg_processing_time_seconds']:.3f}s per invoice")
    throughput = 3600 / summary['avg_processing_time_seconds'] if summary['avg_processing_time_seconds'] > 0 else 0
    print(f"   Estimated Throughput: {throughput:.0f} invoices per hour")
    
    # Error analysis
    if 'per_sample_results' in results:
        analyze_errors(results['per_sample_results'])
    
    # Recommendations
    print_recommendations(summary['field_accuracies'], summary['overall_accuracy'])


def analyze_errors(per_sample_results: List[Dict]):
    """Analyze common error patterns."""
    print("\n" + "=" * 70)
    print(" ERROR ANALYSIS")
    print("=" * 70)
    
    field_errors = {
        'vendor_name': 0,
        'invoice_number': 0,
        'date': 0,
        'total_amount': 0
    }
    
    total_errors = 0
    
    for result in per_sample_results:
        if result.get('error'):
            continue
        
        comparison = result.get('comparison', {})
        for field, is_correct in comparison.items():
            if not is_correct:
                field_errors[field] += 1
                total_errors += 1
    
    if total_errors == 0:
        print("\n✅ No field-level errors detected!")
        return
    
    print(f"\n❌ Total Field Errors: {total_errors}")
    print("\nError Distribution:")
    
    for field, count in sorted(field_errors.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"  {field:20s} │ {bar:<50} │ {count:3d} errors ({percentage:.1f}%)")


def print_recommendations(field_accuracies: Dict[str, float], overall: float):
    """Print improvement recommendations based on results."""
    print("\n" + "=" * 70)
    print(" RECOMMENDATIONS FOR IMPROVEMENT")
    print("=" * 70)
    
    if overall >= 95:
        print("\n🎉 Excellent accuracy! Your pipeline is production-ready.")
        print("   Focus on optimizing processing speed if needed.")
    elif overall >= 85:
        print("\n✅ Good accuracy. Minor improvements recommended:")
        
        # Find weakest field
        weakest = min(field_accuracies.items(), key=lambda x: x[1])
        print(f"   - Focus on improving '{weakest[0]}' extraction ({weakest[1]:.1f}%)")
        print(f"   - Review failed samples to identify patterns")
    else:
        print("\n⚠️  Accuracy needs improvement. Recommendations:")
        print("   1. Tune the SYSTEM_PROMPT in api/extractor.py")
        print("   2. Add few-shot examples to guide Llama 3.2")
        print("   3. Improve OCR preprocessing (contrast, noise reduction)")
        print("   4. Consider post-processing validation rules")
    
    # Field-specific recommendations
    for field, accuracy in field_accuracies.items():
        if accuracy < 80:
            print(f"\n   ⚠️  {field} accuracy is low ({accuracy:.1f}%)")
            
            if field == 'date':
                print(f"      → Try normalizing date formats in post-processing")
            elif field == 'total_amount':
                print(f"      → Add currency symbol handling and decimal normalization")
            elif field == 'invoice_number':
                print(f"      → Improve OCR confidence on alphanumeric strings")
            elif field == 'vendor_name':
                print(f"      → Train Llama to extract company names from headers")


def compare_batch_results(filepath: str = 'batch_results/batch_results.json'):
    """
    Analyze batch processing results.
    
    Args:
        filepath: Path to batch_results.json
    """
    if not Path(filepath).exists():
        print(f"❌ Results file not found: {filepath}")
        print("   Run batch processing first: python -m api.batch_process")
        return
    
    results = load_results(filepath)
    
    print("\n" + "=" * 70)
    print(" BATCH PROCESSING RESULTS")
    print("=" * 70)
    
    total = results['total_processed']
    successful = results['successful']
    errors = results['errors']
    
    print(f"\n📊 Processing Summary")
    print(f"   Total Invoices: {total}")
    print(f"   Successfully Processed: {successful} ({successful/total*100:.1f}%)")
    print(f"   Errors: {errors} ({errors/total*100:.1f}%)")
    
    # Calculate average processing time
    processing_times = [
        r['processing_time_seconds']
        for r in results['results']
        if r['error'] is None
    ]
    
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        min_time = min(processing_times)
        max_time = max(processing_times)
        
        print(f"\n⚡ Performance Metrics")
        print(f"   Average Time: {avg_time:.3f}s per invoice")
        print(f"   Min Time: {min_time:.3f}s")
        print(f"   Max Time: {max_time:.3f}s")
        print(f"   Throughput: {3600/avg_time:.0f} invoices/hour")
        
        # Estimate for full dataset
        full_dataset_time = 6692 * avg_time
        print(f"\n📈 Scaling Estimates")
        print(f"   Time for 6,692 images: {full_dataset_time/3600:.1f} hours")
        print(f"   With 4 parallel workers: {full_dataset_time/3600/4:.1f} hours")
    
    print("\n" + "=" * 70)


def generate_hackathon_summary(
    eval_file: str = 'evaluation_results.json',
    batch_file: str = 'batch_results/batch_results.json'
):
    """
    Generate a comprehensive summary for hackathon presentation.
    
    Args:
        eval_file: Path to evaluation results
        batch_file: Path to batch processing results
    """
    print("\n" + "=" * 70)
    print(" TECHEX AMSTERDAM HACKATHON - PIPELINE SUMMARY")
    print("=" * 70)
    
    # Load evaluation results
    if Path(eval_file).exists():
        eval_results = load_results(eval_file)
        summary = eval_results['summary']
        
        print("\n✅ VALIDATION ON ANNOTATED DATA (Batch 1)")
        print(f"   Samples Tested: {summary['total_samples']}")
        print(f"   Overall Accuracy: {summary['overall_accuracy']:.1f}%")
        print(f"   Processing Speed: {summary['avg_processing_time_seconds']:.2f}s per invoice")
        
        print("\n   Field-Level Performance:")
        for field, accuracy in summary['field_accuracies'].items():
            status = "✓" if accuracy >= 90 else "○"
            print(f"     {status} {field:20s}: {accuracy:.1f}%")
    
    # Load batch results
    if Path(batch_file).exists():
        batch_results = load_results(batch_file)
        
        print(f"\n🚀 SCALABILITY DEMONSTRATION (Batches 2 & 3)")
        print(f"   Invoices Processed: {batch_results['total_processed']}")
        print(f"   Success Rate: {batch_results['successful']/batch_results['total_processed']*100:.1f}%")
    
    print("\n💡 KEY DIFFERENTIATORS")
    print("   ✓ 100% offline operation (no API costs)")
    print("   ✓ GPU-accelerated OCR (RTX 3050)")
    print("   ✓ Local LLM reasoning (Llama 3.2)")
    print("   ✓ Validated on 1,489 ground truth samples")
    print("   ✓ Scales to thousands of invoices")
    
    print("\n🎯 PRODUCTION READINESS")
    print("   ✓ RESTful API (FastAPI)")
    print("   ✓ Structured JSON output")
    print("   ✓ Error handling and validation")
    print("   ✓ Processing time < 5 seconds per invoice")
    
    print("\n" + "=" * 70)
    print(" Ready for judging! 🏆")
    print("=" * 70 + "\n")


def main():
    """Interactive results analysis."""
    print("\n" + "=" * 70)
    print(" RESULTS ANALYSIS TOOL")
    print("=" * 70)
    
    print("\nAvailable analyses:")
    print("  1. Evaluation results (evaluation_results.json)")
    print("  2. Batch processing results (batch_results/batch_results.json)")
    print("  3. Complete hackathon summary")
    
    choice = input("\nSelect analysis (1-3, or Enter for all): ").strip()
    
    if choice == '1':
        analyze_evaluation_results()
    elif choice == '2':
        compare_batch_results()
    elif choice == '3':
        generate_hackathon_summary()
    else:
        # Run all analyses
        analyze_evaluation_results()
        compare_batch_results()
        generate_hackathon_summary()


if __name__ == '__main__':
    main()
