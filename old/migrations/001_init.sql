-- Initial schema for listen (Go rewrite).
-- Keep table/column names aligned with the existing Python/SQLAlchemy models where practical.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT NOT NULL PRIMARY KEY,
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  display_name TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_accessed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL,
  title TEXT,
  audio_file_path TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transcripts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL UNIQUE,
  file_name TEXT NOT NULL,
  transcript_text TEXT NOT NULL,
  duration REAL,
  language TEXT,
  transcription_model TEXT,
  summary TEXT,
  action_items TEXT, -- JSON array stored as text
  audio_file_url TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transcript_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transcript_id INTEGER NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  text TEXT NOT NULL,
  speaker_label TEXT,
  confidence REAL,
  FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS speakers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transcript_id INTEGER NOT NULL,
  speaker_label TEXT NOT NULL,
  segment_count INTEGER NOT NULL DEFAULT 0,
  speaker_metadata TEXT, -- JSON stored as text
  FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER,
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN NOT NULL DEFAULT 1,
  FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS processing_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER,
  transcript_id INTEGER,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  progress INTEGER NOT NULL DEFAULT 0,
  total_chunks INTEGER,
  current_chunk INTEGER,
  result TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
  FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_profiles_is_active ON profiles(is_active);
CREATE INDEX IF NOT EXISTS idx_conversations_profile_id_created ON conversations(profile_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_transcript_id_start ON transcript_segments(transcript_id, start_time);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_conversation_id_created ON processing_jobs(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_profile_id_is_active ON api_keys(profile_id, is_active);

