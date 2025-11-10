"""
Setup script to initialize the project after cloning.
This script creates necessary directories and verifies the setup.
"""

import os
from pathlib import Path

def setup_project():
    """Create necessary directories and verify setup."""
    project_root = Path(__file__).parent
    
    print("🚀 Setting up AI Cost Optimizer project...")
    print(f"📁 Project root: {project_root}")
    
    # Create necessary directories
    directories = [
        project_root / "data" / "runs",
        project_root / "data" / "cache",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Create .gitkeep files to ensure directories are tracked
    for directory in directories:
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
            print(f"✅ Created .gitkeep: {gitkeep}")
    
    # Check if .env file exists
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("\n⚠️  .env file not found!")
        print("📝 Please copy .env.example to .env and add your AWS credentials:")
        print(f"   {env_example} -> {env_file}")
        print("\n   Or run:")
        print("   Windows: Copy-Item .env.example .env")
        print("   Linux/Mac: cp .env.example .env")
    elif env_file.exists():
        print(f"✅ Found .env file: {env_file}")
    else:
        print("⚠️  .env.example not found. Please create .env manually.")
    
    # Check if configs/models.yaml exists
    models_yaml = project_root / "configs" / "models.yaml"
    if models_yaml.exists():
        print(f"✅ Found models configuration: {models_yaml}")
    else:
        print(f"❌ Missing models configuration: {models_yaml}")
        print("   Please ensure configs/models.yaml exists!")
    
    # Check Python version
    import sys
    python_version = sys.version_info
    print(f"\n🐍 Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("⚠️  Warning: Python 3.8+ is recommended")
    else:
        print("✅ Python version is compatible")
    
    print("\n✅ Setup complete!")
    print("\n📚 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Configure AWS credentials in .env file")
    print("3. Run the dashboard: streamlit run src/dashboard.py")
    print("\n📖 For detailed instructions, see README.md")

if __name__ == "__main__":
    setup_project()

