import requests
import pymysql
import os

base_url = "http://localhost:8000/api/v1"

print("Logging in as admin...")
resp = requests.post(f"{base_url}/admin/login", json={"username":"yvezjayveegesmundo", "password":"thethethe"})
token = resp.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

print("Creating announcement...")
ann_payload = {
    "title": "Test Announcement",
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

print("Setting up DB test data...")
# Connect to DB to insert test player and claim record
conn = pymysql.connect(host="127.0.0.1", user="root", password="", database="memory_match", cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cursor:
    cursor.execute("INSERT INTO players (username, display_name, stars, trophies) VALUES ('test_claim_user', 'Test User', 0, 0)")
    player_id = cursor.lastrowid
    
    # Claim endpoint logic expects the claim row to exist or creates it?
    # Wait, the claim endpoint code checks if it exists. If it doesn't, it checks if requirement is met? Let's assume we just call the endpoint.
conn.commit()

# Test 1: claim if completed=False
# The claim endpoint payload: {"player_id": player_id, "completed": False} 
# Wait, let's look at python_api/routers/rewards.py claim_announcement payload.
# I'll just send a POST request with payload {"player_id": player_id}
print("\nTest 1: Claim without completion")
resp1 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": False})
print("Result:", resp1.status_code, resp1.json())

print("\nTest 2: Claim with completion")
# In Memory Match, the frontend probably tells the backend it completed the task, or the backend verifies. Let's send completed: True
resp2 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": True})
print("Result:", resp2.status_code, resp2.json())

print("\nTest 3: Duplicate claim")
resp3 = requests.post(f"{base_url}/rewards/announcements/{ann_id}/claim", json={"player_id": player_id, "completed": True})
print("Result:", resp3.status_code, resp3.json())

conn.close()
