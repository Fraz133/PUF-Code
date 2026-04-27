import requests
import sys

# Change this to your server's URL
SERVER_URL = "http://212.28.191.52:8001"

def check_server():
    print("=" * 60)
    print(f"   PUF SERVER DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"\n[1] Checking Server Connection: {SERVER_URL}...")
    
    try:
        # 1. Health Check
        r = requests.get(SERVER_URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"    [OK] Server is ONLINE (v{data.get('version', 'unknown')})")
            print(f"    [OK] Database Status: {data.get('database', 'unknown')}")
            print(f"    [OK] Registered Tags Count: {data.get('registered_tags_count', 0)}")
            
            # 2. Detailed Tags Check
            print(f"\n[2] Fetching Registered Tags...")
            rt = requests.get(f"{SERVER_URL}/tags", timeout=5)
            if rt.status_code == 200:
                tags = rt.json().get('registered_tags', [])
                if not tags:
                    print("    [!] WARNING: NO TAGS REGISTERED ON SERVER.")
                    print("\n    To solve this, you must run the enrollment script on the server.")
                    print("    Run: 'docker exec -it puf_api python enroll_tags.py'")
                else:
                    print(f"    [OK] Found {len(tags)} tags:")
                    for t in tags:
                        print(f"      > {t['_id']}: {t['count']} time nodes ({sorted(t['time_nodes'])})")
            else:
                print(f"    [ERROR] Could not fetch tags list (HTTP {rt.status_code})")
        else:
            print(f"    [ERROR] Server returned HTTP {r.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"    [ERROR] Could not connect to server. Is it running?")
    except Exception as e:
        print(f"    [ERROR] An unexpected error occurred: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_server()
