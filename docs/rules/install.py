import os
import shutil
import sys
import argparse
from pathlib import Path

def install_rules(languages):
    # Determine the target directory (~/.claude/rules)
    home = Path.home()
    target_dir = home / ".claude" / "rules"
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Current script directory
    script_dir = Path(__file__).parent.absolute()
    
    # 1. Always install common rules
    common_src = script_dir / "common"
    if common_src.exists() and common_src.is_dir():
        print(f"Installing common rules to {target_dir}...")
        # On Windows, we need to handle potential permission issues or existing dirs
        dest = target_dir / "common"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(common_src, dest)
    else:
        print(f"Error: 'common' directory not found at {common_src}")
        sys.exit(1)
        
    # 2. Install requested languages
    for lang in languages:
        lang_src = script_dir / lang
        if lang_src.exists() and lang_src.is_dir():
            print(f"Installing {lang} rules...")
            dest = target_dir / lang
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(lang_src, dest)
        else:
            print(f"Warning: Language directory '{lang}' not found at {lang_src}. Skipping.")

    print(f"\nInstallation complete! Rules are located in: {target_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install Claude rules cross-platform.")
    parser.add_argument("languages",冒险Args="*", help="List of languages to install (e.g., python typescript golang)")
    
    args = parser.parse_args()
    
    try:
        install_rules(args.languages)
    except Exception as e:
        print(f"An error occurred during installation: {e}")
        sys.exit(1)
