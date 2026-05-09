import os
import json
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    """Initializes the Firebase Admin SDK using the service account JSON from ENV or file."""
    if not firebase_admin._apps:
        cred = None
        
        # 1. Try to load from Railway environment variable
        env_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if env_json:
            try:
                # Parse the JSON string from the environment variable
                cert_dict = json.loads(env_json)
                cred = credentials.Certificate(cert_dict)
            except Exception as e:
                print(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON from env: {e}")
                
        # 2. Fallback to local file if no valid env var is found
        if not cred:
            json_path = os.path.join(os.path.dirname(__file__), "firebase_service_account.json")
            if os.path.exists(json_path):
                cred = credentials.Certificate(json_path)

        if cred:
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized successfully.")
        else:
            print("Warning: Firebase credentials not found in ENV or local file. Push notifications will fail.")
