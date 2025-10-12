#!/usr/bin/env python3
"""
Test Donut OCR Integration
Tests the Medical-Prescription-OCR module integration
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_medical_ocr_service():
    """Test Medical OCR Service initialization and basic functionality"""

    print("\n" + "=" * 60)
    print("🧪 Testing Donut OCR Integration")
    print("=" * 60)

    try:
        # Test 1: Import service
        print("\n1️⃣  Testing service import...")
        from src.services.medical_ocr_service import get_medical_ocr_service

        print("   ✅ Medical OCR service imported successfully")

        # Test 2: Initialize service
        print("\n2️⃣  Initializing Medical OCR service...")
        service = get_medical_ocr_service()
        print(f"   ✅ Service initialized")
        print(f"   📍 Model directory: {service.model_dir}")
        print(f"   🖥️  Device: {service.device}")

        # Test 3: Check model files
        print("\n3️⃣  Checking model files...")
        if service.model_dir.exists():
            model_files = list(service.model_dir.glob("*"))
            if model_files:
                print(f"   ✅ Model directory exists with {len(model_files)} files")
                for f in model_files[:5]:  # Show first 5 files
                    print(f"      - {f.name}")
            else:
                print("   ⚠️  Model directory exists but is empty")
                print("   💡 Run: python src/ml_models/medical_ocr/model_download.py")
                return False
        else:
            print(f"   ❌ Model directory not found: {service.model_dir}")
            print("   💡 Run: python src/ml_models/medical_ocr/model_download.py")
            return False

        # Test 4: Test with sample image (if available)
        print("\n4️⃣  Testing OCR extraction...")
        test_images = [
            "tests/sample_prescription.jpg",
            "tests/samples/prescription_1.jpg",
            "data/test_prescription.jpg",
        ]

        test_image = None
        for img_path in test_images:
            if os.path.exists(img_path):
                test_image = img_path
                break

        if test_image:
            print(f"   📄 Processing: {test_image}")
            result = service.process_prescription(test_image)

            print(f"\n   Results:")
            print(f"   ✅ Success: {result['success']}")
            print(f"   📊 Confidence: {result['confidence']:.2%}")
            print(f"   📝 Is Prescription: {result['is_prescription']}")
            print(f"   🤖 Model: {result['model']}")
            print(f"   🖥️  Device: {result['device']}")

            if result["success"]:
                text = result["extracted_text"]
                print(f"\n   📄 Extracted Text ({len(text)} chars):")
                print(f"   {text[:200]}...")

                # Test structured data extraction
                print(f"\n5️⃣  Testing structured data extraction...")
                structured = service.extract_structured_data(text)
                print(
                    f"   ✅ Medications found: {len(structured.get('medications', []))}"
                )
                print(
                    f"   ✅ Instructions found: {len(structured.get('instructions', []))}"
                )

                if structured.get("medications"):
                    print(f"\n   💊 Sample medication:")
                    med = structured["medications"][0]
                    for key, value in med.items():
                        if value:
                            print(f"      {key}: {value}")
            else:
                print(f"   ❌ Error: {result.get('error')}")
                return False
        else:
            print("   ⚠️  No test image found")
            print("   💡 Add a sample prescription image to tests/ to test OCR")
            print("   ✅ Service initialization successful (OCR test skipped)")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True

    except ImportError as e:
        print(f"\n   ❌ Import error: {e}")
        print("\n   💡 Install dependencies:")
        print("      pip install transformers torch torchvision pillow sentencepiece")
        return False

    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_hybrid_ocr_service():
    """Test Hybrid OCR Service"""

    print("\n" + "=" * 60)
    print("🧪 Testing Hybrid OCR Service")
    print("=" * 60)

    try:
        print("\n1️⃣  Testing hybrid service import...")
        from src.services.ocr_service_hybrid import get_ocr_service

        print("   ✅ Hybrid OCR service imported successfully")

        print("\n2️⃣  Initializing hybrid service...")
        service = get_ocr_service()
        print(f"   ✅ Service initialized (default engine: {service.default_engine})")

        print("\n" + "=" * 60)
        print("✅ Hybrid OCR service tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Donut OCR Integration Tests\n")

    # Test Medical OCR
    test1_passed = test_medical_ocr_service()

    # Test Hybrid OCR
    test2_passed = test_hybrid_ocr_service()

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Medical OCR Service: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Hybrid OCR Service:  {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("\n🎉 All integration tests passed!")
        print("\n📝 Next steps:")
        print("   1. Update your routes to use the new OCR service")
        print("   2. Test with real prescription images")
        print("   3. Deploy to staging environment")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")
        sys.exit(1)
