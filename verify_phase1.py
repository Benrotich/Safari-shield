#!/usr/bin/env python3
"""
Verify that Phase 1 setup is complete.
"""
import sys
from pathlib import Path

def check_file_exists(path, description):
    """Check if file exists and print status."""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def main():
    print("=" * 60)
    print("SAFARI-SHIELD: PHASE 1 COMPLETION VERIFICATION")
    print("=" * 60)
    
    checks = []
    
    # Check project structure
    print("\n📁 PROJECT STRUCTURE:")
    checks.append(check_file_exists("requirements.txt", "Requirements file"))
    checks.append(check_file_exists("setup.py", "Setup script"))
    checks.append(check_file_exists(".gitignore", "Git ignore file"))
    checks.append(check_file_exists(".vscode/settings.json", "VS Code settings"))
    checks.append(check_file_exists("src/data/__init__.py", "Data module init"))
    checks.append(check_file_exists("src/data/schemas.py", "Data schemas"))
    checks.append(check_file_exists("src/data/synthetic_generator.py", "Data generator"))
    checks.append(check_file_exists("notebooks/01_data_exploration.ipynb", "Exploration notebook"))
    
    # Check generated data
    print("\n📊 GENERATED DATA:")
    checks.append(check_file_exists("data/synthetic/mpesa_sample.csv", "Sample dataset"))
    checks.append(check_file_exists("data/synthetic/metadata.json", "Dataset metadata"))
    
    # Check Python environment
    print("\n🐍 PYTHON ENVIRONMENT:")
    try:
        import pandas
        print(f"✅ Pandas installed: {pandas.__version__}")
    except ImportError:
        print("❌ Pandas not installed")
        checks.append(False)
    
    try:
        
        from src.data.synthetic_generator import MPesaDataGenerator  # noqa: F401
        print("✅ Data generator import successful")
    except ImportError as e:
        print(f"❌ Data generator import failed: {e}")
        checks.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY:")
    print("=" * 60)
    
    success_count = sum(checks)
    total_checks = len(checks)
    
    if success_count == total_checks:
        print(f"🎉 ALL CHECKS PASSED! ({success_count}/{total_checks})")
        print("\nPhase 1 setup is complete! You can now:")
        print("1. Explore data in notebooks/01_data_exploration.ipynb")
        print("2. Generate more data: python run_data_generation.py")
        print("3. Move to Phase 2: Feature Engineering")
        return 0
    else:
        print(f"⚠️  {success_count}/{total_checks} checks passed")
        print("\nPlease fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())