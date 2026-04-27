"""
Image Processor Module
======================
Reusable functions that take ANY PUF image and return ALL THREE key types
required by the client's cloud authentication system:

  1. Binary Keys    - 4x 30x30 grids of 1s and 0s (one per color channel)
  2. M-ary Key      - 1x 30x30 grid (time-node dependent encoding base)
  3. Grayscale Grid  - 4x 30x30 grids of 0-255 intensity (for PMF comparison)

Flow: Raw Image -> 4 Color Channels -> Binary Keys + M-ary Key + Grayscale Grid
"""

import cv2
import numpy as np
import os
import sys
import tempfile

# Add algorithms path for M-ary extractor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'algorithms', 'm_ary_key_coding'))
from m_ary_extractor import generate_mary_key_timenode


# ============================================================
# STEP 1: Color Channel Extraction
# ============================================================
def extract_color_channels(image_path):
    """
    Takes any PUF image and separates it into 4 color channel masks.
    Returns a dictionary of 4 clean binary masks + the original image.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Sharpness preservation: use a lighter blur for distinct particles
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # STRICT ranges to prevent color bleeding
    # Higher S_MIN and V_MIN to ignore background noise/glow
    S_MIN, V_MIN = 80, 60 
    merged_ranges = {
        'Blue':           ((95, S_MIN, V_MIN), (135, 255, 255)),
        'Green':          ((40, S_MIN, V_MIN), (90, 255, 255)),
        'Yellow':         ((15, S_MIN, V_MIN), (38, 255, 255)),
        'Red':            [((0, S_MIN, V_MIN), (12, 255, 255)), 
                           ((150, S_MIN, V_MIN), (180, 255, 255))]
    }

    channel_masks = {}

    for channel_name, bounds in merged_ranges.items():
        # Create the HSV mask
        if isinstance(bounds, list):
            mask = cv2.bitwise_or(
                cv2.inRange(hsv, bounds[0][0], bounds[0][1]),
                cv2.inRange(hsv, bounds[1][0], bounds[1][1])
            )
        else:
            mask = cv2.inRange(hsv, bounds[0], bounds[1])

        # Minimal Cleaning to avoid "condensing" particles
        # We only remove extremely tiny noise (area < 5 pixels)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        clean_mask = np.zeros_like(mask)
        for cnt in contours:
            if cv2.contourArea(cnt) > 5:
                cv2.drawContours(clean_mask, [cnt], -1, 255, thickness=-1)

        channel_masks[channel_name] = clean_mask

    return channel_masks, img


# ============================================================
# STEP 2: Binary Key Generation (Key Type 1)
# ============================================================
def generate_binary_keys(channel_masks, grid_size=30):
    """
    Takes the 4 color channel masks and converts each into a 
    granular Binary Key grid (1s and 0s) using density thresholding.
    Matches professor's MATLAB 'QR-style' look.
    """
    binary_keys = {}
    threshold = 30  # concentration threshold (~12%)

    for channel_name, mask in channel_masks.items():
        # Resize using INTER_AREA to compute density within each grid cell
        # Values in resized will be 0-255 representing concentration
        resized = cv2.resize(mask, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
        
        # Apply threshold: only cells with enough color pixels become '1'
        binary_grid = (resized > threshold).astype(np.uint8)
        binary_keys[channel_name] = binary_grid

    return binary_keys


# ============================================================
# STEP 3: M-ary Key Generation (Key Type 2)
# ============================================================
# Now handled by algorithms/m_ary_key_coding/m_ary_extractor.py
# Uses professor's time-node-dependent encoding:
#   0.1s -> Base-16 (Hex)     | 1s -> Base-8 (Octal)
#   2s   -> Base-4 (Quat)     | 3s+ -> Base-10 (Decimal)


# ============================================================
# STEP 4: Grayscale Intensity Grid (For PMF Key Type 3)
# ============================================================
def generate_grayscale_grids(channel_masks, original_img, grid_size=30):
    """
    For each color channel, calculate the AVERAGE grayscale intensity (0-255) 
    within each grid cell. This represents the physical brightness of the 
    phosphorescent particles, which is what decays over time.
    
    Returns: { 'Blue': 30x30 array (0-255), ... }
    """
    gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    grayscale_grids = {}
    
    for channel_name, mask in channel_masks.items():
        h, w = mask.shape[:2]
        cell_h = h / grid_size
        cell_w = w / grid_size
        
        intensity_grid = np.zeros((grid_size, grid_size), dtype=np.float64)
        
        for r in range(grid_size):
            for c in range(grid_size):
                y1, y2 = int(r * cell_h), int((r + 1) * cell_h)
                x1, x2 = int(c * cell_w), int((c + 1) * cell_w)
                
                cell_mask = mask[y1:y2, x1:x2]
                cell_gray = gray[y1:y2, x1:x2]
                
                # Only calculate average intensity where the mask is active
                active_pixels = cell_gray[cell_mask > 0]
                if len(active_pixels) > 0:
                    intensity_grid[r, c] = np.mean(active_pixels)
                else:
                    intensity_grid[r, c] = 0.0
        
        grayscale_grids[channel_name] = intensity_grid
    
    return grayscale_grids


# ============================================================
# MASTER PIPELINE: Extract ALL 3 Key Types
# ============================================================
def process_puf_image(image_path, grid_size=30, time_node=0.1):
    """
    Master function: Takes any PUF image path and returns ALL THREE key types.
    
    Args:
        image_path: Path to the PUF tag image (can be .png or .jpeg)
        grid_size: Size of the key grids (default 30x30)
        time_node: Time in seconds after UV off (determines M-ary encoding base)
    
    Returns:
        dict with:
            'binary_keys':     { 4 channel names -> 30x30 arrays of 0/1 }
            'mary_key':        30x30 array (values depend on time node)
            'mary_base':       int (4, 8, 10, or 16)
            'mary_encoding':   str description of encoding used
            'grayscale_grids': { 4 channel names -> 30x30 arrays of 0-255 }
    """
    # Step 1: Extract color channels
    channel_masks, original_img = extract_color_channels(image_path)
    
    # Step 2: Generate Binary Keys (Key Type 1)
    binary_keys = generate_binary_keys(channel_masks, grid_size)
    
    # Step 3: Generate M-ary Key (Key Type 2) - Professor's time-node encoding
    mary_result = generate_mary_key_timenode(image_path, time_node, grid_size=30)
    mary_key = mary_result['mary_key']
    mary_base = mary_result['mary_base']
    mary_encoding = mary_result['encoding']
    
    # Step 4: Generate Grayscale Intensity Grids (for PMF - Key Type 3)
    grayscale_grids = generate_grayscale_grids(channel_masks, original_img, grid_size)
    
    # Print summary
    print(f"\n  Processed: {os.path.basename(image_path)}")
    for name, key in binary_keys.items():
        print(f"    {name:>15s}: {np.sum(key)} bits active out of {grid_size*grid_size}")
    print(f"    {'M-ary Key':>15s}: {mary_encoding} | {np.count_nonzero(mary_key)} cells active, max={np.max(mary_key)}")
    
    return {
        'binary_keys': binary_keys,
        'mary_key': mary_key,
        'mary_base': mary_base,
        'mary_encoding': mary_encoding,
        'grayscale_grids': grayscale_grids
    }


def process_uploaded_bytes(image_bytes, grid_size=30, time_node=0.1):
    """
    Same as process_puf_image but accepts raw bytes (from a FastAPI upload).
    Saves to a temp file, processes, then cleans up.
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode uploaded image bytes")
    
    # Save to a temporary file so we can reuse the same pipeline
    temp_path = os.path.join(tempfile.gettempdir(), "puf_upload_temp.png")
    cv2.imwrite(temp_path, img)
    
    try:
        result = process_puf_image(temp_path, grid_size, time_node=time_node)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return result


# Quick test when run directly
if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(__file__), '..', '04_Sample_Data', 'raw_images', 'tag_00.jpeg')
    test_path = os.path.abspath(test_path)
    print(f"Testing with: {test_path}")
    result = process_puf_image(test_path, time_node=0.1)
    
    print("\n--- Binary Keys ---")
    for name, key in result['binary_keys'].items():
        print(f"  {name}: shape={key.shape}, ones={np.sum(key)}")
    
    print(f"\n--- M-ary Key ---")
    print(f"  Shape: {result['mary_key'].shape}, Base: {result['mary_base']}, Encoding: {result['mary_encoding']}")
    print(f"  Unique values: {np.unique(result['mary_key'])}")
    
    print(f"\n--- Grayscale Grids ---")
    for name, grid in result['grayscale_grids'].items():
        print(f"  {name}: shape={grid.shape}, mean intensity={np.mean(grid[grid>0]):.1f}")
