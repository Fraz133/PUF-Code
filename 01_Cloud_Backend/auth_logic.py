"""
Authentication Logic Module (Triple-Key Architecture)
======================================================
Core logic for comparing Binary, M-ary, and PMF keys.
Uses high-accuracy mathematical models to verify PUF tag authenticity.
"""

import numpy as np
from pmf_engine import compare_pmf_direct

def compare_binary_keys(extracted_key, reference_key):
    """
    Compare two binary key grids using Jaccard Similarity.
    Intersection over Union — only looks at active '1' bits.
    """
    ext = np.array(extracted_key).flatten()
    ref = np.array(reference_key).flatten()
    
    if len(ext) != len(ref):
        return 0.0
    
    # Jaccard = (ext AND ref) / (ext OR ref)
    intersection = np.sum((ext == 1) & (ref == 1))
    union = np.sum((ext == 1) | (ref == 1))
    
    if union == 0:
        return 100.0 if np.sum(ext) == 0 else 0.0
        
    match_percentage = (intersection / union) * 100
    return float(round(match_percentage, 2))


def compare_mary_keys(extracted_mary, reference_mary):
    """
    Compare two M-ary (0-15) keys using cell-by-cell matching.
    Returns the percentage of pixels that match exactly.
    """
    ext = np.array(extracted_mary).flatten()
    ref = np.array(reference_mary).flatten()
    
    if len(ext) != len(ref):
        return 0.0
        
    # Count EXACT matches (0-15)
    matches = np.sum(ext == ref)
    total = len(ext)
    
    match_percentage = (matches / total) * 100
    return float(round(match_percentage, 2))


def verify_binary_keys(extracted_binary_keys, ref_binary_keys, threshold=85.0):
    """
    Compare all 4 binary key channels.
    Returns: (all_passed, channel_scores, overall_score)
    """
    channel_scores = {}
    all_passed = True
    
    # The 4 color channels we extract from the PUF
    channels = ['Blue', 'Green', 'Yellow', 'Red']
    
    for channel_name in channels:
        extracted = extracted_binary_keys.get(channel_name)
        reference = ref_binary_keys.get(channel_name)
        
        if extracted is None or reference is None:
            channel_scores[channel_name] = {"match_percent": 0.0, "passed": False, "reason": "Channel not found"}
            all_passed = False
            continue
        
        match_percent = compare_binary_keys(extracted, reference)
        passed = bool(match_percent >= threshold)
        
        channel_scores[channel_name] = {"match_percent": float(match_percent), "passed": passed}
        if not passed:
            all_passed = False
    
    # Calculate overall average score
    scores = [ch["match_percent"] for ch in channel_scores.values()]
    overall = float(round(sum(scores) / len(scores), 2)) if scores else 0.0
    
    return bool(all_passed), channel_scores, overall


def verify_mary_keys(extracted_mary, ref_mary, threshold=85.0):
    """
    Real M-ary verification (0-15 grid).
    """
    if extracted_mary is None or ref_mary is None:
        return False, 0.0
        
    match_percent = compare_mary_keys(extracted_mary, ref_mary)
    passed = bool(match_percent >= threshold)
    
    return passed, match_percent


def verify_pmf_keys(extracted_grayscale, reference_grayscale, threshold=75.0):
    """
    Direct PMF verification by comparing the extracted grayscale grid 
    against the actual enrolled grayscale grid for this time node.
    """
    if not extracted_grayscale or not reference_grayscale:
        return False, 0.0
        
    # 1. Compare extracted vs actual enrolled reference
    _, overall_score = compare_pmf_direct(extracted_grayscale, reference_grayscale)
    
    # 2. Apply threshold
    passed = bool(overall_score >= threshold)
    return passed, overall_score


def identify_and_verify_tag(extracted_data, time_node, all_tags_reference_data, threshold=85.0):
    """
    Auto-detects which tag matches the extracted triple-key data.
    Attempts to find the best match across all registered tags.
    """
    best_tag_id = "Unknown"
    highest_score = -1.0
    best_result = {
        "is_authenticated": False,
        "binary": {"passed": False, "score": 0.0, "details": {}},
        "mary": {"passed": False, "score": 0.0},
        "pmf": {"passed": False, "score": 0.0}
    }
    
    for tag_id, tag_ref in all_tags_reference_data.items():
        # 1. Binary Check (85% Threshold)
        ref_binary = tag_ref.get('binary_keys', {})
        b_passed, b_scores, b_overall = verify_binary_keys(
            extracted_data['binary_keys'], ref_binary, threshold
        )
        
        # 2. M-ary Check (85% Threshold)
        ref_mary = tag_ref.get('mary_key')
        m_passed, m_score = verify_mary_keys(extracted_data['mary_key'], ref_mary, threshold)
        
        # 3. PMF Check (75% Threshold for direct grayscale comparison)
        ref_grayscale = tag_ref.get('grayscale_ref', {})
        p_passed, p_score = verify_pmf_keys(extracted_data['grayscale_grids'], ref_grayscale, threshold=75.0)
        
        # Overall Authentication: Must pass ALL THREE keys
        is_authenticated = b_passed and m_passed and p_passed
        
        # Track the best match based on binary/overall score
        if b_overall > highest_score:
            highest_score = b_overall
            best_tag_id = tag_id
            best_result = {
                "is_authenticated": is_authenticated,
                "binary": {"passed": b_passed, "score": b_overall, "details": b_scores},
                "mary": {"passed": m_passed, "score": m_score},
                "pmf": {"passed": p_passed, "score": p_score}
            }
            
    return best_tag_id, best_result
