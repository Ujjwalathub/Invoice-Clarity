"""
Voxel51 Invoice Dataset Loader

Downloads and manages the Voxel51 high-quality invoice images dataset
from Hugging Face. This dataset contains 8,181 synthetic invoice images
with 1,489 fully annotated samples (Batch 1) and 6,692 unannotated images
(Batches 2 & 3).
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from datasets import load_dataset
from PIL import Image


class Voxel51InvoiceDataset:
    """
    Manages the Voxel51 invoice dataset for training and evaluation.
    
    The dataset structure:
    - Batch 1 (1,489 images): Fully annotated with ground truth JSON
    - Batches 2 & 3 (6,692 images): Raw images only
    
    Total size: ~2 GB
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the dataset loader.
        
        Args:
            cache_dir: Optional directory to cache the dataset. 
                      Defaults to ~/.cache/huggingface/datasets
        """
        self.cache_dir = cache_dir
        self.dataset = None
        self._loaded = False
    
    def load(self, force_reload: bool = False) -> None:
        """
        Download and load the Voxel51 invoice dataset.
        
        Args:
            force_reload: If True, re-download the dataset even if cached
        """
        if self._loaded and not force_reload:
            return
        
        print("Loading Voxel51 invoice dataset from Hugging Face...")
        print("This is a ~2 GB download and may take several minutes on first run.")
        
        self.dataset = load_dataset(
            "Voxel51/high-quality-invoice-images-for-ocr",
            cache_dir=self.cache_dir
        )
        self._loaded = True
        
        # Print dataset info
        train_size = len(self.dataset['train']) if 'train' in self.dataset else 0
        print(f"✓ Dataset loaded successfully!")
        print(f"  - Training samples (annotated): {train_size}")
        
        if 'test' in self.dataset:
            test_size = len(self.dataset['test'])
            print(f"  - Test samples: {test_size}")
    
    def get_annotated_samples(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get the fully annotated invoice samples (Batch 1).
        
        Args:
            limit: Optional limit on number of samples to return
        
        Returns:
            List of dictionaries containing image, filepath, and ground_truth
        """
        if not self._loaded:
            self.load()
        
        train_split = self.dataset['train']
        samples = []
        
        count = limit if limit else len(train_split)
        
        for i in range(min(count, len(train_split))):
            sample = train_split[i]
            samples.append({
                'image': sample['image'],
                'filepath': sample.get('filepath', f'sample_{i}'),
                'ground_truth': sample.get('ground_truth', {})
            })
        
        return samples
    
    def get_unannotated_samples(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get the unannotated invoice samples (Batches 2 & 3).
        
        Note: These samples only contain images without ground truth labels.
        Use these to demonstrate scalability on fresh data.
        
        Args:
            limit: Optional limit on number of samples to return
        
        Returns:
            List of dictionaries containing image and filepath
        """
        if not self._loaded:
            self.load()
        
        # Check if there's a separate split for unannotated data
        if 'test' in self.dataset:
            split = self.dataset['test']
        else:
            # If no test split, return empty list
            return []
        
        samples = []
        count = limit if limit else len(split)
        
        for i in range(min(count, len(split))):
            sample = split[i]
            samples.append({
                'image': sample['image'],
                'filepath': sample.get('filepath', f'unannotated_{i}')
            })
        
        return samples
    
    def get_sample(self, index: int, split: str = 'train') -> Dict:
        """
        Get a single sample from the dataset.
        
        Args:
            index: Sample index
            split: Dataset split ('train' or 'test')
        
        Returns:
            Dictionary containing image, filepath, and ground_truth (if available)
        """
        if not self._loaded:
            self.load()
        
        sample = self.dataset[split][index]
        
        return {
            'image': sample['image'],
            'filepath': sample.get('filepath', f'{split}_{index}'),
            'ground_truth': sample.get('ground_truth', None)
        }
    
    def export_sample_images(self, output_dir: str, num_samples: int = 10) -> None:
        """
        Export sample images to a directory for manual inspection.
        
        Args:
            output_dir: Directory to save images
            num_samples: Number of samples to export
        """
        if not self._loaded:
            self.load()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        samples = self.get_annotated_samples(limit=num_samples)
        
        for i, sample in enumerate(samples):
            # Save image
            img = sample['image']
            if isinstance(img, Image.Image):
                img.save(output_path / f"sample_{i:04d}.png")
            
            # Save ground truth JSON
            if sample['ground_truth']:
                with open(output_path / f"sample_{i:04d}.json", 'w') as f:
                    json.dump(sample['ground_truth'], f, indent=2)
        
        print(f"✓ Exported {num_samples} samples to {output_dir}")


def quick_test():
    """Quick test to verify dataset loading works correctly."""
    print("=" * 60)
    print("Voxel51 Invoice Dataset - Quick Test")
    print("=" * 60)
    
    loader = Voxel51InvoiceDataset()
    loader.load()
    
    # Get first annotated sample
    sample = loader.get_sample(0, split='train')
    
    print("\nFirst sample information:")
    print(f"  - Filepath: {sample['filepath']}")
    print(f"  - Image size: {sample['image'].size if hasattr(sample['image'], 'size') else 'N/A'}")
    print(f"  - Has ground truth: {sample['ground_truth'] is not None}")
    
    if sample['ground_truth']:
        print(f"\nGround truth data:")
        print(json.dumps(sample['ground_truth'], indent=2))
    
    print("\n" + "=" * 60)
    print("✓ Dataset is ready for use!")
    print("=" * 60)


if __name__ == '__main__':
    quick_test()
