"""
PUF Cloud Authentication API (Secure Triple-Key Version)
=========================================================
FastAPI backend that verifies PUF tag authenticity using a combination
of Binary Keys, M-ary Keys, and PMF Temporal Response.

Security: X-API-KEY header required.
"""

import os
import sys

# Add this directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from typing import Optional
import uvicorn

from image_processor import process_uploaded_bytes
from database import (
    get_tag_reference, 
    get_available_time_nodes, 
    get_closest_time_node,
    get_all_tags_at_time,
    get_all_registered_tags,
    log_authentication_attempt,
    get_pmf_params,
    check_db_connection
)
from auth_logic import (
    verify_binary_keys, 
    verify_mary_keys, 
    verify_pmf_keys, 
    identify_and_verify_tag
)

from fastapi.middleware.cors import CORSMiddleware

# --- APP INIT ---
app = FastAPI(
    title="PUF Authentication API",
    description="Verification using Binary, M-ary, and PMF keys.",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint with database connectivity check."""
    db_ok, db_msg = check_db_connection()
    # Get tag count if DB is OK
    tag_count = 0
    if db_ok:
        try:
            from database import get_all_registered_tags
            tag_count = len(get_all_registered_tags())
        except:
            pass
            
    return {
        "status": "online" if db_ok else "degraded",
        "database": db_msg,
        "registered_tags_count": tag_count,
        "version": "2.1.2"
    }


@app.get("/tags")
async def list_tags():
    """List all registered tags and their time nodes."""
    try:
        tags = get_all_registered_tags()
        return {"registered_tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/authenticate")
async def authenticate_puf(
    image: UploadFile = File(..., description="The PUF tag image captured after UV excitation"),
    time_node: float = Form(..., description="Time in seconds after UV was turned off (e.g. 3.0)"),
    tag_id: Optional[str] = Form(None, description="The PUF tag ID. If omitted, the system will auto-detect.")
):
    """
    PUF Authentication Endpoint.
    Integrates Binary Keys + M-ary Key + PMF Response.
    """
    
    # 1. Extract Data from uploaded image
    try:
        image_bytes = await image.read()
        extracted_data = process_uploaded_bytes(image_bytes, time_node=time_node)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")

    
    # 2. Identify & Verify Logic
    threshold = 85.0
    
    if tag_id:
        # Scenario A: Tag ID provided
        available_times = get_available_time_nodes(tag_id)
        if not available_times:
            raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found.")
            
        matched_time = get_closest_time_node(tag_id, time_node)
        db_data = get_tag_reference(tag_id, matched_time)
        pmf_params_doc = get_pmf_params(tag_id)
        pmf_params = pmf_params_doc.get('pmf_params') if pmf_params_doc else None
        
        # Binary Verification (Actual)
        b_passed, b_scores, b_overall = verify_binary_keys(
            extracted_data['binary_keys'], db_data.get('binary_keys'), threshold=threshold
        )
        
        # M-ary Verification (Actual)
        m_passed, m_score = verify_mary_keys(
            extracted_data['mary_key'], db_data.get('mary_key'), threshold=threshold
        )
        
        # PMF Verification (Actual)
        p_passed, p_score = verify_pmf_keys(
            extracted_data['grayscale_grids'], db_data.get('grayscale_ref'), threshold=75.0
        )
        
        auth_result = {
            "is_authenticated": b_passed and m_passed and p_passed,
            "binary": {"passed": b_passed, "score": b_overall, "details": b_scores},
            "mary": {"passed": m_passed, "score": m_score},
            "pmf": {"passed": p_passed, "score": p_score}
        }
        final_tag_id = tag_id
        final_matched_time = matched_time
    else:
        # Scenario B: Auto-Detect
        all_refs = get_all_tags_at_time(time_node)
        
        if not all_refs:
            raise HTTPException(
                status_code=404, 
                detail="No registered tags found on this server. Please ensure the enrollment script has been run on the server's database."
            )
            
        final_tag_id, auth_result = identify_and_verify_tag(
            extracted_data, time_node, all_refs, threshold=threshold
        )
        final_matched_time = get_closest_time_node(final_tag_id, time_node)
    
    # 3. Format Response
    channel_breakdown = {}
    for ch, details in auth_result['binary']['details'].items():
        channel_breakdown[ch] = {
            "match": f"{details.get('match_percent', 0.0)}%",
            "status": "PASS" if details.get('passed', False) else "FAIL"
        }
        
    response = {
        "authentication": "PASSED" if auth_result['is_authenticated'] else "FAILED",
        "tag_id": final_tag_id,
        "matched_against_time_node": str(final_matched_time),
        "key_1_binary": {
            "result": "PASS" if auth_result['binary']['passed'] else "FAIL",
            "overall_score": auth_result['binary']['score'],
            "threshold": threshold,
            "breakdown": channel_breakdown
        },
        "key_2_mary": {
            "result": "PASS" if auth_result['mary']['passed'] else "FAIL",
            "overall_score": auth_result['mary']['score'],
            "threshold": threshold
        },
        "key_3_pmf": {
            "result": "PASS" if auth_result['pmf']['passed'] else "FAIL",
            "overall_score": auth_result['pmf']['score'],
            "threshold": 75.0
        },
        "security": {
            "api_authentication": "Disabled (Test Mode)",
            "triple_key_check": "Active (85% Threshold)"
        }
    }
    
    # 4. Log attempt
    log_authentication_attempt(
        tag_id=final_tag_id,
        time_node=time_node,
        result=response["authentication"],
        scores={
            "binary": auth_result['binary']['score'],
            "mary": auth_result['mary']['score'],
            "pmf": auth_result['pmf']['score']
        }
    )
    print(f"[AUTH] Result: {response['authentication']}")
    print("-" * 60)
    
    return response


if __name__ == "__main__":
    print("Starting Secure PUF Backend on Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
