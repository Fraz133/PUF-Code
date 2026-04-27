"""
Database Module
===============
Handles MongoDB connection and all database operations.
Stores and retrieves ALL THREE key types for PUF tag authentication:

  1. Binary Keys  — 4× 30x30 grids of 0/1
  2. M-ary Key    — 1× 30x30 grid of 0–15
  3. PMF Params   — 4× sets of (A, τ, C) parameter grids
  4. Grayscale Ref — 4× 30x30 grids of 0–255 intensity

Database Structure:
    Database: puf_authentication_db
    Collection: registered_tags
    
    Each document = {
        "puf_tag_id": "TAG-001",
        "time_node": 0.1,
        "binary_keys": {
            "Blue_Cyan": [[0,1,0,...], ...],      # 30x30 grid
            "Green": [[1,0,0,...], ...],           # 30x30 grid  
            "Yellow_Orange": [[0,0,1,...], ...],   # 30x30 grid
            "Red_Purple": [[1,1,0,...], ...],      # 30x30 grid
        },
        "mary_key": [[8,4,0,12,...], ...],         # 30x30 grid (0–15)
        "grayscale_ref": {
            "Blue_Cyan": [[45.2, 120.5,...], ...], # 30x30 grid (0–255)
            ...
        },
        "enrollment_date": "2026-04-18",
        "source_image": "tag_00.jpeg"
    }
    
    Collection: pmf_models
    
    Each document = {
        "puf_tag_id": "TAG-001",
        "pmf_params": {
            "Blue_Cyan":  { "A": [[...]], "tau": [[...]], "C": [[...]] },
            "Green":      { "A": [[...]], "tau": [[...]], "C": [[...]] },
            ...
        }
    }
"""

from pymongo import MongoClient
from datetime import datetime
import numpy as np

import os

# Database Connection Logic
# Locally, it uses localhost. In Docker/Cloud, it uses the MONGO_URL environment variable.
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(mongo_url)

# Create (or connect to) our project database
db = client['puf_authentication_db']

# Collections
tags_collection = db['registered_tags']
pmf_collection = db['pmf_models']
logs_collection = db['authentication_logs']

def check_db_connection():
    """Checks if the MongoDB server is reachable."""
    try:
        # The admin.command("ping") is the fastest way to check connection
        client.admin.command('ping')
        return True, "Connected to MongoDB"
    except Exception as e:
        return False, f"Database Error: {str(e)}"


# ============================================================
# STORE: Enrollment Data
# ============================================================
def store_tag_data(tag_id, time_node, binary_keys, mary_key, grayscale_grids, source_image="unknown"):
    """
    Store ALL key types for a specific tag at a specific time node.
    
    Args:
        tag_id: e.g. "TAG-001"
        time_node: e.g. 0.1 (seconds after UV excitation)
        binary_keys: dict of 4 numpy arrays (32x32 each, 0/1)
        mary_key: numpy array (32x32, 0â€“15)
        grayscale_grids: dict of 4 numpy arrays (32x32 each, 0â€“255)
        source_image: filename of the original image
    """
    # Convert numpy arrays to regular Python lists for MongoDB storage
    binary_as_lists = {}
    for channel_name, key_array in binary_keys.items():
        binary_as_lists[channel_name] = key_array.tolist()
    
    gray_as_lists = {}
    for channel_name, grid in grayscale_grids.items():
        gray_as_lists[channel_name] = grid.tolist()
    
    document = {
        "puf_tag_id": tag_id,
        "time_node": time_node,
        "binary_keys": binary_as_lists,
        "mary_key": mary_key.tolist(),
        "grayscale_ref": gray_as_lists,
        "enrollment_date": datetime.now().isoformat(),
        "source_image": source_image
    }
    
    # Remove old entry for same tag+time_node if it exists (upsert)
    tags_collection.delete_many({
        "puf_tag_id": tag_id, 
        "time_node": time_node
    })
    
    result = tags_collection.insert_one(document)
    print(f"  [DB] Stored {tag_id} at t={time_node}s â†’ MongoDB ID: {result.inserted_id}")
    return result.inserted_id


def store_pmf_params(tag_id, pmf_params):
    """
    Store the fitted PMF decay parameters for a tag.
    These are tag-wide (not per time-node), since they model the decay ACROSS all times.
    
    Args:
        tag_id: e.g. "TAG-001"
        pmf_params: dict { channel: { 'A': grid, 'tau': grid, 'C': grid } }
    """
    params_as_lists = {}
    for channel_name, params in pmf_params.items():
        params_as_lists[channel_name] = {
            'A': params['A'].tolist(),
            'tau': params['tau'].tolist(),
            'C': params['C'].tolist()
        }
    
    # Remove old PMF model for this tag
    pmf_collection.delete_many({"puf_tag_id": tag_id})
    
    document = {
        "puf_tag_id": tag_id,
        "pmf_params": params_as_lists,
        "fitted_date": datetime.now().isoformat()
    }
    
    result = pmf_collection.insert_one(document)
    print(f"  [DB] Stored PMF model for {tag_id} â†’ MongoDB ID: {result.inserted_id}")
    return result.inserted_id


# ============================================================
# RETRIEVE: Authentication Data
# ============================================================
def get_tag_reference(tag_id, time_node):
    """
    Retrieve the stored reference data for a specific tag at a specific time node.
    Returns the full document with binary_keys, mary_key, and grayscale_ref.
    """
    doc = tags_collection.find_one({
        "puf_tag_id": tag_id,
        "time_node": time_node
    })
    
    if doc:
        # Convert lists back to numpy arrays
        if 'binary_keys' in doc:
            for channel_name in doc['binary_keys']:
                doc['binary_keys'][channel_name] = np.array(doc['binary_keys'][channel_name])
        
        if 'mary_key' in doc:
            doc['mary_key'] = np.array(doc['mary_key'])
        
        if 'grayscale_ref' in doc:
            for channel_name in doc['grayscale_ref']:
                doc['grayscale_ref'][channel_name] = np.array(doc['grayscale_ref'][channel_name])
    
    return doc


def get_pmf_params(tag_id):
    """
    Retrieve the stored PMF decay parameters for a tag.
    """
    doc = pmf_collection.find_one({"puf_tag_id": tag_id})
    
    if doc and 'pmf_params' in doc:
        for channel_name in doc['pmf_params']:
            for param_name in ['A', 'tau', 'C']:
                doc['pmf_params'][channel_name][param_name] = np.array(
                    doc['pmf_params'][channel_name][param_name]
                )
    
    return doc


def get_available_time_nodes(tag_id):
    """Get all available time nodes for a specific tag."""
    docs = tags_collection.find(
        {"puf_tag_id": tag_id}, 
        {"time_node": 1, "_id": 0}
    )
    return sorted([doc['time_node'] for doc in docs])


def get_closest_time_node(tag_id, requested_time):
    """Find the closest registered time node for a tag."""
    available = get_available_time_nodes(tag_id)
    if not available:
        return None
    closest = min(available, key=lambda x: abs(x - requested_time))
    return closest


def get_all_registered_tags():
    """Get a summary of all registered tags and their time nodes."""
    pipeline = [
        {"$group": {
            "_id": "$puf_tag_id",
            "time_nodes": {"$push": "$time_node"},
            "count": {"$sum": 1}
        }}
    ]
    return list(tags_collection.aggregate(pipeline))


def get_all_tags_at_time(requested_time):
    """
    Retrieve all registered tags' data for the closest matching time node.
    Returns: dict { tag_id: reference_data_doc }
    """
    all_tags = get_all_registered_tags()
    results = {}
    
    for tag_summary in all_tags:
        tag_id = tag_summary['_id']
        matched_time = get_closest_time_node(tag_id, requested_time)
        if matched_time is not None:
            ref = get_tag_reference(tag_id, matched_time)
            if ref:
                results[tag_id] = ref
    
    return results


def get_all_pmf_models():
    """Retrieve all PMF models from the database."""
    models = pmf_collection.find({})
    results = {}
    
    for doc in models:
        tag_id = doc['puf_tag_id']
        # Convert lists back to numpy
        if 'pmf_params' in doc:
            for channel_name in doc['pmf_params']:
                for param_name in ['A', 'tau', 'C']:
                    doc['pmf_params'][channel_name][param_name] = np.array(
                        doc['pmf_params'][channel_name][param_name]
                    )
            results[tag_id] = doc['pmf_params']
            
    return results


def log_authentication_attempt(tag_id, time_node, result, scores):
    """Log every authentication attempt for audit trail."""
    log_entry = {
        "puf_tag_id": tag_id,
        "time_node": time_node,
        "result": result,
        "scores": scores,
        "timestamp": datetime.now().isoformat()
    }
    logs_collection.insert_one(log_entry)


def clear_all_data():
    """Clear all data from the database. USE WITH CAUTION."""
    tags_collection.delete_many({})
    pmf_collection.delete_many({})
    logs_collection.delete_many({})
    print("[WARNING] All database data cleared.")


if __name__ == "__main__":
    print("Database module loaded successfully.")
    print(f"Connected to: mongodb://localhost:27017/puf_authentication_db")
    
    tags = get_all_registered_tags()
    if tags:
        print(f"\nRegistered tags:")
        for tag in tags:
            print(f"  {tag['_id']}: {tag['count']} time nodes â†’ {sorted(tag['time_nodes'])}")
    else:
        print("\nNo tags registered yet. Run enroll_tags.py to register.")

