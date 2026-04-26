from pymongo import MongoClient
import pprint

import os

def inspect_database():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
    client = MongoClient(mongo_url)
    db = client['puf_authentication_db']
    
    print("=" * 60)
    print("        PUF DATABASE INSPECTOR (30x30 Standard)")
    print("=" * 60)
    
    # 1. Check Registered Tags
    tags = list(db.registered_tags.find({}, {"binary_keys": 0, "mary_key": 0, "grayscale_ref": 0}))
    
    if not tags:
        print("\n[!] No tags found in 'registered_tags' collection.")
    else:
        print(f"\n[OK] Found {len(tags)} registered time-node samples:")
        for tag in tags:
            print(f"  > Tag: {tag['puf_tag_id']} | Time: {tag['time_node']}s | Enrolled: {tag['enrollment_date'][:19]}")

    # 2. Check a single sample's structure to prove 30x30 storage
    sample = db.registered_tags.find_one({"time_node": 2.0})
    if sample:
        print(f"\n[PROOF] Verifying data structure for t=2.0s:")
        mary_grid = sample['mary_key']
        print(f"  - M-ary Grid Shape: {len(mary_grid)}x{len(mary_grid[0])} (Standardized 30x30)")
        print(f"  - Binary Keys: {list(sample['binary_keys'].keys())} (4 Channels)")
        
    # 3. Check PMF Models
    models = list(db.pmf_models.find({}, {"pmf_params": 0}))
    print(f"\n[OK] Found {len(models)} PMF Decay Models:")
    for model in models:
        print(f"  > Model for Tag: {model['puf_tag_id']} | Created: {model['fitted_date'][:19]}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    inspect_database()
