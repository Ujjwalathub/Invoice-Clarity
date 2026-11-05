"""
Export Sample Invoices to sample_invoices/ Directory

This script exports invoice images from the Voxel51 dataset
to the sample_invoices/ directory for use in the Streamlit UI.
"""
from pathlib import Path

from api.dataset_loader import Voxel51InvoiceDataset


def export_sample_invoices(num_samples: int = 10):
    """
    Export sample invoices for Streamlit UI demonstration.
    
    Args:
        num_samples: Number of invoice samples to export (default: 10)
    """
    print("=" * 70)
    print(" EXPORT SAMPLE INVOICES FOR UI")
    print("=" * 70)
    
    output_dir = Path("sample_invoices")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nLoading Voxel51 dataset...")
    dataset = Voxel51InvoiceDataset()
    dataset.load()
    
    print(f"Exporting {num_samples} invoice samples to {output_dir}/")
    dataset.export_sample_images(str(output_dir), num_samples=num_samples)
    
    # Count exported files
    image_files = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
    json_files = list(output_dir.glob("*.json"))
    
    print("\n" + "=" * 70)
    print(" EXPORT COMPLETE")
    print("=" * 70)
    print(f"\n✅ Exported {len(image_files)} invoice images")
    print(f"✅ Exported {len(json_files)} ground truth JSON files")
    print(f"\n📁 Location: {output_dir.absolute()}")
    print("\nYou can now use these samples in the Streamlit UI:")
    print("  streamlit run ui/app.py")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Export 10 samples by default
    # Change this number if you want more samples
    export_sample_invoices(num_samples=10)
