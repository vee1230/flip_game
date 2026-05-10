import requests
import pymysql
import os

base_url = "https://endearing-optimism-production-6a15.up.railway.app/api/v1"

print("Logging in as admin...")
resp = requests.post(f"{base_url}/admin/login", json={"username":"yvezjayveegesmundo", "password":"thethethe"})
token = resp.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

print("Creating announcement on production...")
ann_payload = {
    "title": "Prod Test Announcement",
    "task_description": "Do something",
    "reward_type": "stars",
    "reward_amount": 50,
    "difficulty_target": "Any",
    "theme_target": "Any",
    "start_date": "2026-01-01T00:00:00",
    "end_date": "2026-12-31T23:59:59",
    "notification_message": "test"
}
resp = requests.post(f"{base_url}/admin/reward-announcements", json=ann_payload, headers=headers)
print("Create Announcement:", resp.status_code, resp.json())
ann_id = resp.json().get("id")

# Since we can't easily access the prod DB to insert a fake player directly, 
# let's just use player_id = 1, assuming there is at least one player or admin.
player_id = 1 

print("\nTest 1: Claim without completion")
resp1 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": False})
print("Result 1 (expect 400 not completed):", resp1.status_code, resp1.text)

print("\nTest 2: Claim with completion")
resp2 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": True})
print("Result 2 (expect 200 success or 404 player not found):", resp2.status_code, resp2.text)

print("\nTest 3: Duplicate claim")
resp3 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": True})
print("Result 3 (expect 400 already claimed or 404):", resp3.status_code, resp3.text)
