import requests

base_url = "http://localhost:8000/api/v1"

print("1. Testing Admin Login")
try:
    resp = requests.post(f"{base_url}/admin/login", json={"username":"yvezjayveegesmundo", "password":"thethethe"})
    resp_json = resp.json()
    print("Login Status:", resp.status_code)
    
    if "token" not in resp_json:
        print("Failed to get token:", resp_json)
        exit(1)
        
    token = resp_json["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        "/admin/leaderboard",
        "/admin/analytics/overview",
        "/admin/reward-announcements",
        "/admin/multiplayer-matches",
        "/admin/recent-activity"
    ]
    
    for ep in endpoints:
        print(f"\n2. Testing GET {ep}")
        res = requests.get(f"{base_url}{ep}", headers=headers)
        print("Status:", res.status_code)
        if res.status_code != 200:
            print("Response:", res.text)
        else:
            data = res.json()
            if isinstance(data, list):
                print(f"Success! Returned list with {len(data)} items.")
            elif isinstance(data, dict):
                print(f"Success! Returned dict with keys: {list(data.keys())}")
            else:
                print(f"Success! Returned data: {data}")

except Exception as e:
    print("Error:", e)
