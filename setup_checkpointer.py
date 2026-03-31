"""
Setup Helper: Install Missing Dependencies
───────────────────────────────────────────
Run this script to install all LangGraph checkpoint dependencies.
"""
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install missing packages for LangGraph checkpointing."""
    
    print("🔧 Installing LangGraph Checkpoint Dependencies...\n")
    
    packages = [
        "langgraph-checkpoint-sqlite",
    ]
    
    failed = []
    for pkg in packages:
        print(f"  Installing {pkg}...", end=" ")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
            print("✅")
        except subprocess.CalledProcessError as e:
            print("❌")
            failed.append(pkg)
    
    print()
    if failed:
        print(f"❌ Failed to install: {', '.join(failed)}")
        print("\n📝 Manual installation:")
        for pkg in failed:
            print(f"   pip install {pkg}")
        return False
    else:
        print("✅ All dependencies installed successfully!\n")
        print("📋  You can now run:")
        print("   python test_checkpointer.py")
        print("   python test_checkpointer_integration.py")
        return True


if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
