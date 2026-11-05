"""
Quick Start Script for Voxel51 Dataset Integration

This script guides you through the complete setup and testing process
for the TechEx Amsterdam hackathon demo.
"""
import sys
import time


def print_header(text: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70 + "\n")


def print_step(number: int, text: str):
    """Print a numbered step."""
    print(f"\n{'─' * 70}")
    print(f"STEP {number}: {text}")
    print('─' * 70)


def check_dependencies():
    """Check if required packages are installed."""
    print_step(1, "Checking Dependencies")
    
    required = {
        'fastapi': 'FastAPI',
        'easyocr': 'EasyOCR',
        'ollama': 'Ollama',
        'datasets': 'Hugging Face Datasets',
        'PIL': 'Pillow'
    }
    
    missing = []
    
    for package, name in required.items():
        try:
            __import__(package)
            print(f"  ✓ {name} is installed")
        except ImportError:
            print(f"  ✗ {name} is NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies are installed!")
        return True


def test_ollama():
    """Test if Ollama is running with llama3.2."""
    print_step(2, "Testing Ollama Service")
    
    try:
        import ollama
        
        print("  Checking Ollama connection...")
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': 'Hello'}]
        )
        print("  ✓ Ollama is running")
        print("  ✓ llama3.2 model is available")
        print("\n✅ Ollama service is ready!")
        return True
    
    except Exception as e:
        print(f"  ✗ Ollama test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Install Ollama from https://ollama.ai")
        print("  2. Run: ollama pull llama3.2")
        print("  3. Ensure Ollama is running in the background")
        return False


def test_dataset():
    """Test dataset loading."""
    print_step(3, "Testing Dataset Loading")
    
    try:
        from api.dataset_loader import Voxel51InvoiceDataset
        
        print("  Loading Voxel51 dataset (this may take a few minutes on first run)...")
        dataset = Voxel51InvoiceDataset()
        dataset.load()
        
        print("  ✓ Dataset downloaded and loaded")
        
        # Get a sample
        sample = dataset.get_sample(0, split='train')
        print(f"  ✓ Retrieved sample: {sample['filepath']}")
        print(f"  ✓ Ground truth available: {sample['ground_truth'] is not None}")
        
        print("\n✅ Dataset is ready!")
        return True
    
    except Exception as e:
        print(f"  ✗ Dataset test failed: {e}")
        print("\nThis is likely a network issue. The dataset will be cached after first download.")
        return False


def run_quick_evaluation():
    """Run a quick evaluation on 5 samples."""
    print_step(4, "Running Quick Evaluation (5 samples)")
    
    try:
        from api.evaluate import InvoiceEvaluator
        
        print("  Initializing evaluator...")
        evaluator = InvoiceEvaluator()
        
        print("  Processing 5 invoice samples...")
        print("  (This tests your complete pipeline: EasyOCR → Llama 3.2 → JSON)\n")
        
        metrics = evaluator.run_evaluation(num_samples=5)
        
        print("\nQuick Results:")
        print(f"  Overall Accuracy: {metrics['summary']['overall_accuracy']:.1f}%")
        print(f"  Successful Extractions: {metrics['summary']['successful']}/5")
        print(f"  Avg Processing Time: {metrics['summary']['avg_processing_time_seconds']:.2f}s")
        
        print("\n✅ Pipeline is working!")
        return True
    
    except Exception as e:
        print(f"  ✗ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the complete quick start sequence."""
    print_header("VOXEL51 INVOICE DATASET - QUICK START")
    print("This script will verify your setup for the TechEx Amsterdam hackathon.")
    print("Estimated time: 5-10 minutes (first run includes dataset download)")
    
    start_time = time.time()
    
    # Step 1: Dependencies
    if not check_dependencies():
        print("\n❌ Setup incomplete. Please install missing dependencies first.")
        sys.exit(1)
    
    # Step 2: Ollama
    if not test_ollama():
        print("\n❌ Setup incomplete. Please configure Ollama first.")
        sys.exit(1)
    
    # Step 3: Dataset
    if not test_dataset():
        print("\n⚠️  Dataset loading failed, but you can continue.")
        print("   The dataset will be downloaded when you run evaluation.")
    
    # Step 4: Quick eval
    if not run_quick_evaluation():
        print("\n❌ Evaluation failed. Please check the error messages above.")
        sys.exit(1)
    
    # Success!
    elapsed = time.time() - start_time
    
    print_header("SETUP COMPLETE!")
    print(f"✅ Your invoice extraction pipeline is ready for the hackathon!")
    print(f"⏱️  Total setup time: {elapsed:.1f} seconds\n")
    
    print("Next steps:")
    print("\n  📊 Run full evaluation (50 samples):")
    print("     python -m api.evaluate")
    
    print("\n  🚀 Batch process invoices:")
    print("     python -m api.batch_process")
    
    print("\n  🌐 Start the API server:")
    print("     uvicorn api.main:app --host 0.0.0.0 --port 8000")
    
    print("\n  📈 Improve accuracy:")
    print("     - Tune the SYSTEM_PROMPT in api/extractor.py")
    print("     - Experiment with different OCR preprocessing")
    print("     - Try temperature adjustments in Ollama calls")
    
    print("\n" + "=" * 70)
    print("Good luck at TechEx Amsterdam! 🚀")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
