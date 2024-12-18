import os
from pathlib import Path
from database.models import Base
from database.database import engine, SQLALCHEMY_DATABASE_URL

def setup_database(reset: bool = False):
    """Setup and initialize the database
    
    Args:
        reset (bool): If True, drops all existing tables before creating new ones
    """
    if reset:
        # For SQLite, we can just delete the database file
        if SQLALCHEMY_DATABASE_URL.startswith('sqlite:///'):
            db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"Removed existing database at {db_path}")
        else:
            # For other databases, drop all tables
            Base.metadata.drop_all(bind=engine)
            print("Dropped all existing tables")
    
    # Create data directory if it doesn't exist (for SQLite)
    if SQLALCHEMY_DATABASE_URL.startswith('sqlite:///'):
        db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    setup_database()
