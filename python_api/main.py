"""
Memory Match Puzzle — Python FastAPI Backend
============================================
Replaces the PHP backend for academic purposes (System Integration criteria).
Runs on http://localhost:8000
Docs at  http://localhost:8000/docs
"""

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, admin, notifications, scores, ml, users, multiplayer, rewards
from models.models import load_models
from database import init_db

app = FastAPI(
    title="Memory Match Puzzle API",
    description="Core Python service powering both the Web and Mobile interfaces.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    """Load all ML models into memory and initialize database schemas when the server starts."""
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed (non-fatal): {e}")
    try:
        load_models()
    except Exception as e:
        print(f"Warning: ML model loading failed (non-fatal): {e}")

# Allow frontend origins (Vercel + local dev)
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1",
    "https://flip-game-eta.vercel.app",
    "https://flip-game.vercel.app",
    os.getenv("FRONTEND_URL", ""),  # Set this in Render env vars
]
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o]  # remove empty strings

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,          prefix="/api/v1/auth",          tags=["Authentication"])
app.include_router(users.router,         prefix="/api/v1/users",         tags=["Users"])
app.include_router(scores.router,        prefix="/api/v1/scores",        tags=["Scores"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(admin.router,         prefix="/api/v1/admin",         tags=["Admin Dashboard"])
app.include_router(ml.router,            prefix="/api/v1/ml",            tags=["Machine Learning"])
app.include_router(multiplayer.router,   prefix="/api/v1/multiplayer",   tags=["Multiplayer"])
app.include_router(rewards.router,       prefix="/api/v1/rewards",       tags=["Rewards"])


@app.get("/", tags=["Root"])
def root():
    return {"message": "Memory Match Puzzle API is running!", "version": "1.0.0"}
