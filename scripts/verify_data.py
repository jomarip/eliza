#!/usr/bin/env python3
"""Verify Hatchyverse data files and structure."""

import os
from pathlib import Path
import logging

def verify_data_structure():
    """Verify all required data files exist."""
    base_dir = Path("data/lore/official_canon")
    required_files = [
        "Hatchy - Monster Data - gen 1.csv",
        "Hatchy - Monster Data - gen 2.csv",
        "Gen3 List  - Asset list .csv",
        "Hatchipedia - Factions and groups.csv",
        "Hatchipedia - famous champions.csv",
        "Hatchipedia - nations and politics.csv"
    ]
    
    missing = []
    for file in required_files:
        if not (base_dir / file).exists():
            missing.append(file)
            
    if missing:
        print("Missing required data files:")
        for file in missing:
            print(f"- {file}")
        print("\nPlease ensure all data files are in data/lore/official_canon/")
        return False
        
    return True

if __name__ == "__main__":
    if not verify_data_structure():
        exit(1)
    print("All required data files present!") 