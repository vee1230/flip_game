import requests
import time
import sys

base_url = "https://endearing-optimism-production-6a15.up.railway.app/api/v1"

print("Waiting for Railway deployment to finish...")
max_retries = 30 # 30 * 10 = 300s = 5 minutes
token = None

for i in range(max_retries):
    try:
        resp = requests.post(f"{base_url}/admin/login", json={"username":"yvezjayveegesmundo", "password":"thethethe"})
        if resp.status_code == 200 and "token" in resp.json():
            token = resp.json()["token"]
            
            # Check if leaderboard exists (which proves PR #2 is deployed, as it didn't exist before)
            lb_resp = requests.get(f"{base_url}/admin/leaderboard", headers={"Authorization": f"Bearer {token}"})
            if lb_resp.status_code == 200:
                print("\n✅ Deployment detected! Endpoints are live.\n")
                break
    except Exception:
        pass
    
    print(f"[{i+1}/{max_retries}] Waiting for Railway deployment (checking again in 10s)...")
    time.sleep(10)

if not token:
    print("❌ Failed to get token or deployment did not finish in time.")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}
endpoints = [
    "/admin/leaderboard",
    "/admin/analytics/overview",
    "/admin/reward-announcements",
    "/admin/multiplayer-matches",
    "/admin/recent-activity"
]

all_passed = True
for ep in endpoints:
    print(f"Testing GET {ep}")
    res = requests.get(f"{base_url}{ep}", headers=headers)
    if res.status_code == 200:
        print(f"  ✅ Status: 200 OK")
    else:
        print(f"  ❌ Status: {res.status_code} - Response: {res.text}")
        all_passed = False

if all_passed:
    print("\n✅ All admin endpoints are functioning correctly on Railway!")
else:
    print("\n❌ Some admin endpoints failed.")
    sys.exit(1)
