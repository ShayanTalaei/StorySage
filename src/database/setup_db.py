import os
from pathlib import Path
from database.init_db import init_db
from database.database import SQLALCHEMY_DATABASE_URL

def setup_database():
    # Extract database path from URL for SQLite
    if SQLALCHEMY_DATABASE_URL.startswith('sqlite:///'):
        db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
        
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"Setting up SQLite database at: {db_path}")
    
    # Initialize database tables
    init_db()
    print("Database tables created successfully!")
