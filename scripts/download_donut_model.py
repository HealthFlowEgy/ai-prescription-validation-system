#!/usr/bin/env python3
"""
Download Donut OCR model from Hugging Face
Model: chinmays18/medical-prescription-ocr
"""

import os
import sys
from pathlib import Path


def download_model():
    """Download and cache Donut model"""

    model_name = "chinmays18/medical-prescription-ocr"
    cache_dir = Path("src/ml_models/donut_ocr")
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("📥 Downloading Donut OCR Model")
    print("=" * 60)
    print(f"   Model: {model_name}")
    print(f"   Cache: {cache_dir}")
    print(f"   Size: ~800 MB (this may take a few minutes)")
    print()

    try:
        from transformers import DonutProcessor, VisionEncoderDecoderModel

        # Download processor
        print("⏬ Downloading processor...")
        processor = DonutProcessor.from_pretrained(model_name, cache_dir=str(cache_dir))
        print("✅ Processor downloaded successfully")
        print()

        # Download model
        print("⏬ Downloading model (this may take several minutes)...")
        model = VisionEncoderDecoderModel.from_pretrained(
            model_name, cache_dir=str(cache_dir)
        )
        print("✅ Model downloaded successfully")
        print()

        print("=" * 60)
        print("✅ Donut OCR model successfully downloaded!")
        print("=" * 60)
        print(f"   Location: {cache_dir.absolute()}")
        print(f"   Model: {model_name}")
        print()
        print("You can now use the Donut OCR service in your application.")
        print()

        return True

    except ImportError as e:
        print("❌ Error: Required packages not installed")
        print()
        print("Please install dependencies first:")
        print("   pip install -r requirements-donut.txt")
        print()
        return False

    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check your internet connection")
        print("2. Ensure you have enough disk space (~1 GB)")
        print("3. Try again - downloads can sometimes timeout")
        print()
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
