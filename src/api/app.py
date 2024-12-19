from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database.setup_db import SQLALCHEMY_DATABASE_URL
from api.routers import chat, auth

app = FastAPI(title="AI Autobiography API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    """Check if database exists on startup"""
    if SQLALCHEMY_DATABASE_URL.startswith('sqlite:///'):
        db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            raise Exception(
                "Database not found! Please run 'python src/main.py --mode setup_db' "
                "to initialize the database."
            )

# Include routers
app.include_router(chat.router)
app.include_router(auth.router)