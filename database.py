"""Database setup and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
from config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    
    # Migration: Update processing_jobs table schema
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    if 'processing_jobs' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('processing_jobs')}
        
        # Add conversation_id column if it doesn't exist
        if 'conversation_id' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE processing_jobs ADD COLUMN conversation_id INTEGER"))
                conn.commit()
                print("Added conversation_id column to processing_jobs table")
        
        # Add progress column if it doesn't exist
        if 'progress' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE processing_jobs ADD COLUMN progress INTEGER DEFAULT 0"))
                conn.commit()
                print("Added progress column to processing_jobs table")
        
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Check if transcript_id is NOT NULL when it should be nullable
        if 'transcript_id' in columns and not columns['transcript_id'].get('nullable', True):
            # Recreate table with correct schema
            with engine.connect() as conn:
                # Create new table with correct schema
                conn.execute(text("""
                    CREATE TABLE processing_jobs_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        conversation_id INTEGER,
                        transcript_id INTEGER,
                        job_type VARCHAR NOT NULL,
                        status VARCHAR,
                        progress INTEGER DEFAULT 0,
                        result TEXT,
                        created_at DATETIME
                    )
                """))
                
                # Copy data
                conn.execute(text("""
                    INSERT INTO processing_jobs_new 
                    (id, conversation_id, transcript_id, job_type, status, progress, result, created_at)
                    SELECT 
                        id, 
                        NULL as conversation_id,
                        transcript_id,
                        job_type,
                        status,
                        COALESCE(progress, 0) as progress,
                        result,
                        created_at
                    FROM processing_jobs
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE processing_jobs"))
                
                # Rename new table
                conn.execute(text("ALTER TABLE processing_jobs_new RENAME TO processing_jobs"))
                
                conn.commit()
                print("Updated processing_jobs table schema")
