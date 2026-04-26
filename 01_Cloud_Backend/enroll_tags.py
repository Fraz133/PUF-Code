"""
Enrollment Script
=================
Processes ALL tag images from the raw_images folder and stores their 
complete key data (Binary + M-ary + Grayscale + PMF) into MongoDB.

This is run ONCE to "register" the tag in the database.
After this, the FastAPI server can verify any new uploaded image 
using ALL THREE cryptographic key types.

Images available (same physical tag at different timestamps):
    tag_00.jpeg -> t = 0.1s  (brightest, just after UV off)
    tag_03.jpeg -> t = 1.5s
    tag_04.jpeg -> t = 3.0s
    tag_05.jpeg -> t = 4.5s
    tag_07.jpeg -> t = 6.0s  (dimmest, mostly blue remaining)
"""

import os
import sys

# Add this directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from image_processor import process_puf_image
from pmf_engine import fit_pmf_parameters
from database import (
    store_tag_data, 
    store_pmf_params,
    get_all_registered_tags, 
    clear_all_data
)

# ============================================================
# CONFIGURATION
# ============================================================
TAG_ID = "TAG-001"

IMAGE_TIME_MAP = {
    "1 (2).jpg": 0.1,  # Hexadecimal
    "1 (3).jpg": 1.0,  # Octal
    "1 (4).jpg": 2.0,  # Quaternary
    "1 (5).jpg": 3.0,  # Decimal
    "1 (6).jpg": 4.0,  # Decimal
}

# Path to the representative images directory
# For cloud deployment, we expect images to be in a 'data' folder inside the backend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_IMAGES_DIR = os.path.join(BASE_DIR, "data")


def enroll_tag():
    """
    Process all tag images and store their complete key data in MongoDB.
    Also fits the PMF decay curves across all time nodes.
    """
    print("=" * 60)
    print("  PUF TAG ENROLLMENT (Triple-Key System)")
    print("  Registering Binary Keys + M-ary Key + PMF Model")
    print("=" * 60)
    
    raw_dir = os.path.abspath(RAW_IMAGES_DIR)
    print(f"\n[DIR] Looking for images in: {raw_dir}")
    
    if not os.path.exists(raw_dir):
        print(f"[ERROR] Directory not found: {raw_dir}")
        return
    
    # Clear old data for clean enrollment
    clear_all_data()
    
    enrolled_count = 0
    time_nodes = []
    
    # Collect grayscale grids across all time nodes for PMF fitting
    # Structure: { 'Blue_Cyan': [grid_t0, grid_t1, ...], ... }
    all_grayscale_over_time = {
        'Blue': [], 'Green': [], 'Yellow': [], 'Red': []
    }
    
    for filename, time_node in IMAGE_TIME_MAP.items():
        image_path = os.path.join(raw_dir, filename)
        
        if not os.path.exists(image_path):
            print(f"\n[SKIP] Skipping {filename} - file not found")
            continue
        
        print(f"\n{'-' * 50}")
        print(f"[IMG] Processing: {filename} (Time Node = {time_node}s)")
        print(f"{'-' * 50}")
        
        try:
            # Extract ALL 3 key types from the image
            result = process_puf_image(image_path, grid_size=30, time_node=time_node)
            
            binary_keys = result['binary_keys']
            mary_key = result['mary_key']
            grayscale_grids = result['grayscale_grids']
            
            # Store in MongoDB (Binary Keys + M-ary Key + Grayscale Reference)
            store_tag_data(
                tag_id=TAG_ID,
                time_node=time_node,
                binary_keys=binary_keys,
                mary_key=mary_key,
                grayscale_grids=grayscale_grids,
                source_image=filename
            )
            
            # Collect grayscale grids for later PMF fitting
            for channel_name in all_grayscale_over_time:
                all_grayscale_over_time[channel_name].append(grayscale_grids[channel_name])
            
            time_nodes.append(time_node)
            enrolled_count += 1
            
        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================================
    # FIT PMF DECAY CURVES
    # ============================================================
    if enrolled_count >= 2:
        print(f"\n{'=' * 50}")
        print(f"  FITTING PMF DECAY CURVES")
        print(f"  Using {enrolled_count} time nodes: {time_nodes}")
        print(f"{'=' * 50}")
        
        pmf_params = fit_pmf_parameters(all_grayscale_over_time, time_nodes)
        store_pmf_params(TAG_ID, pmf_params)
        
        print(f"\n  [OK] PMF decay model fitted and stored in MongoDB!")
    else:
        print(f"\n  [WARN] Need at least 2 time nodes to fit PMF curves. Got {enrolled_count}.")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"  ENROLLMENT COMPLETE")
    print(f"  Tag: {TAG_ID}")
    print(f"  Time nodes enrolled: {enrolled_count}/{len(IMAGE_TIME_MAP)}")
    print(f"  Keys stored: Binary + M-ary + Grayscale + PMF Model")
    print(f"{'=' * 60}")
    
    # Verify what's in the database
    print(f"\n[DB] Database Summary:")
    tags = get_all_registered_tags()
    for tag in tags:
        print(f"  {tag['_id']}: {tag['count']} time nodes â†’ {sorted(tag['time_nodes'])}")


if __name__ == "__main__":
    enroll_tag()

