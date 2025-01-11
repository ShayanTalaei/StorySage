from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from database.setup_db import SQLALCHEMY_DATABASE_URL
from api.routers import chat, auth, biography

app = FastAPI(title="AI Autobiography API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Changed to False since we're using "*" for origins
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(biography.router)