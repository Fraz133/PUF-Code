"""
M-ary Key Extractor  –  Professor's Time-Node Encoding (Python port)
=====================================================================
Faithful Python translation of the MATLAB function `PUF_TimeNode_Encoding`.

Encoding rules (from professor's MATLAB code):
   0.1 s → Hexadecimal (Base-16)  – 4 color channels visible
   1   s → Octal (Base-8)         – 3 channels visible
   2   s → Quaternary (Base-4)    – 2 channels visible
   3   s → Decimal (Base-10)      – intensity thresholding (blue only)

Grid size: 30×30 (matching professor's specification)

Key implementation details matching the MATLAB original:
  - Grayscale conversion: 0.2989*R + 0.5870*G + 0.1140*B  (MATLAB standard)
  - Resize: bicubic spline interpolation via meshgrid + linspace
            (matches MATLAB's interp2(..., 'cubic'))
  - Normalize: min-max to [0, 1]
  - Hex/Octal/Quat: round(imgNorm * (M-1))
  - Decimal: histcounts with linearly-spaced edges, edges[0]=-inf, edges[-1]=inf
"""

import cv2
import numpy as np
from scipy.interpolate import RectBivariateSpline


# ──────────────────────────────────────────────────────────────
# TIME-NODE → ENCODING BASE MAPPING
# ──────────────────────────────────────────────────────────────
def get_encoding_base(time_node):
    """
    Maps a time node to the correct M-ary encoding base.

    Professor's valid times: 0.1, 1, 2, 3
    Our system times:        0.1, 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1

    Mapping logic (based on physical phosphor decay):
        t < 0.5s  → Base-16 (Hex)    – All 4 phosphor colors visible
        t < 1.5s  → Base-8  (Octal)  – 3 colors remaining
        t < 2.5s  → Base-4  (Quat)   – 2 colors remaining
        t >= 2.5s → Base-10 (Dec)    – Only blue intensity left
    """
    if time_node < 0.5:
        return 16, "Hexadecimal (Base-16)"
    elif time_node < 1.5:
        return 8, "Octal (Base-8)"
    elif time_node < 2.5:
        return 4, "Quaternary (Base-4)"
    else:
        return 10, "Decimal (Base-10)"


# ──────────────────────────────────────────────────────────────
# CORE ENCODING FUNCTION  (mirrors MATLAB PUF_TimeNode_Encoding)
# ──────────────────────────────────────────────────────────────
def generate_mary_key_timenode(image_input, time_node, grid_size=30):
    """
    Professor's Time-Node M-ary Encoding (Python port of MATLAB original).

    Converts a PUF image to a 30×30 encoded matrix where the encoding
    base depends on the time node (how long after UV excitation).

    Args:
        image_input: File path (str) or numpy image array (BGR from OpenCV)
        time_node:   Time in seconds after UV off (e.g. 0.1, 1.1, 2.1, etc.)
        grid_size:   Grid dimensions (default 30×30 per professor's spec)

    Returns:
        dict with:
            'mary_key':   np.array (30×30) with values 0 to M-1
            'mary_base':  int (4, 8, 10, or 16)
            'encoding':   str description
    """

    # ── 1. Load Image ──────────────────────────────────────────
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            raise ValueError(f"Could not load image from {image_input}")
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        raise TypeError("Input must be a filename string or a numpy image array.")

    # ── 2. Convert to Grayscale (MATLAB weights) ──────────────
    # MATLAB: imgGray = 0.2989*R + 0.5870*G + 0.1140*B → uint8
    # OpenCV loads as BGR, so: channel 2=R, 1=G, 0=B
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_gray = (0.2989 * img[:, :, 2].astype(np.float64) +   # R
                    0.5870 * img[:, :, 1].astype(np.float64) +   # G
                    0.1140 * img[:, :, 0].astype(np.float64))    # B
        img_gray = np.clip(np.round(img_gray), 0, 255).astype(np.uint8)
    else:
        img_gray = img.astype(np.uint8) if img.dtype != np.uint8 else img

    # ── 3. Resize to 30×30 via Bicubic Spline Interpolation ───
    # Replicates MATLAB:
    #   [Xq, Yq] = meshgrid(linspace(1, origW, 30), linspace(1, origH, 30));
    #   imgResized = interp2(double(imgGray), Xq, Yq, 'cubic');
    orig_h, orig_w = img_gray.shape[:2]

    # MATLAB uses 1-based indices; we use 0-based
    y_orig = np.arange(orig_h, dtype=np.float64)       # 0 .. origH-1
    x_orig = np.arange(orig_w, dtype=np.float64)       # 0 .. origW-1

    # Build the bicubic spline over the original grid
    spline = RectBivariateSpline(y_orig, x_orig,
                                 img_gray.astype(np.float64), kx=3, ky=3)

    # Query points (matching MATLAB's linspace(1, origW, 30) but 0-based)
    yq = np.linspace(0, orig_h - 1, grid_size)
    xq = np.linspace(0, orig_w - 1, grid_size)

    img_resized = spline(yq, xq)   # shape: (grid_size, grid_size)

    # ── 4. Normalize to [0, 1] ─────────────────────────────────
    min_val = img_resized.min()
    max_val = img_resized.max()
    if max_val == min_val:
        img_norm = np.zeros_like(img_resized)
    else:
        img_norm = (img_resized - min_val) / (max_val - min_val)

    # ── 5. M-ary Encoding Based on Time Node ──────────────────
    M, encoding_name = get_encoding_base(time_node)

    if M == 10:
        # Decimal (Base-10): histogram binning  (MATLAB's histcounts)
        # edges = linspace(minVal, maxVal, M+1);  edges(1)=-inf; edges(end)=inf;
        edges = np.linspace(min_val, max_val, M + 1)
        edges[0] = -np.inf
        edges[-1] = np.inf
        # np.digitize: bin index starting at 1 → subtract 1 for 0..9
        key_matrix = np.digitize(img_resized.flatten(), edges) - 1
        key_matrix = np.clip(key_matrix, 0, M - 1)
        key_matrix = key_matrix.reshape(grid_size, grid_size).astype(np.uint8)
    else:
        # Hex (16), Octal (8), Quaternary (4): simple quantization
        # MATLAB: keyMatrix = uint8(round(imgNorm * (M-1)));
        key_matrix = np.round(img_norm * (M - 1)).astype(np.uint8)

    return {
        'mary_key': key_matrix,
        'mary_base': M,
        'encoding': encoding_name
    }
