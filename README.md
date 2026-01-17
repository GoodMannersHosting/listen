# Audio Transcription Tool

A modern Python 3.12+ FastAPI web application for transcribing audio files with optional speaker diarization, summarization, and action item extraction. Features a ChatGPT-like interface with conversation history, profile management, and integrated audio playback.

## Features

- **Audio Transcription**: Support for multiple transcription backends (Whisper or Parakeet V3)
- **Speaker Diarization**: Optional speaker identification using pyannote-audio
- **Summarization**: Generate summaries from transcripts using Ollama via OpenWebUI
- **Action Items**: Extract action items from transcripts using LLM
- **ChatGPT-like UI**: Modern interface with conversation history, tabs, and audio playback
- **Profile Management**: Multiple user profiles with independent conversation history
- **Audio Playback**: Integrated audio player with speed and volume controls
- **Multiple Formats**: Support for mp3, m4a, mp4, ogg, wav, flac

## Requirements

- Python 3.12+
- FFmpeg installed on system
- PyTorch (for model inference)
- Ollama service accessible via OpenWebUI endpoint (optional, for summarization/action items)

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone <repository-url>
cd listen
```

3. Install dependencies using uv:
```bash
# Using uv project management (recommended - automatically creates/manages venv)
uv sync

# Or using uv pip with requirements.txt
uv pip install -r requirements.txt
```

uv will automatically create and manage the virtual environment for you.

4. Install FFmpeg:
   - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)

5. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Create a `.env` file or set environment variables:

```env
# Database (defaults to SQLite)
DATABASE_URL=sqlite:///./listen.db

# Transcription Model
TRANSCRIPTION_MODEL=whisper  # or "parakeet"
WHISPER_MODEL=base  # tiny, base, small, medium, large

# Speaker Diarization (optional)
ENABLE_DIARIZATION=false
PYANNOTE_PIPELINE=community-1

# Ollama/OpenWebUI (for summarization/action items)
OPENWEBUI_URL=http://localhost:11434/api/chat
OPENWEBUI_MODEL=llama2
OPENWEBUI_TEMPERATURE=0.7
OPENWEBUI_MAX_TOKENS=2000

# Audio Processing
AUDIO_CHUNK_DURATION=15
UPLOAD_DIR=./uploads
```

## Usage

1. Initialize the database:
```bash
# Using uv
uv run python -c "from database import init_db; init_db()"

# Or if using uv sync, activate the environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -c "from database import init_db; init_db()"
```

2. Start the application:
```bash
# Using uv (recommended)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or if environment is activated
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

## Usage Guide

### Creating a Profile

1. Click "New Profile" in the sidebar
2. Enter a profile name and optional display name
3. Click "Create"

### Uploading and Processing Audio

1. Select or create a profile
2. Click "New Conversation" or use the upload area
3. Drag and drop an audio file or click "Browse Files"
4. Select processing options:
   - Enable Speaker Diarization: Identifies who spoke when
   - Generate Summary: Creates a summary using LLM
   - Generate Action Items: Extracts action items using LLM
5. Click "Upload & Process"

### Viewing Results

After processing, you can:

- **Transcript Tab**: View the full transcript with speaker labels (if diarization enabled) and timestamps
- **Summary Tab**: View the generated summary (if requested)
- **Action Items Tab**: View extracted action items (if requested)
- **Audio Player**: Play back the original audio with speed and volume controls

### Managing Conversations

- Conversations are automatically saved and appear in the sidebar
- Click a conversation to load it
- Conversations are organized by profile

## Transcription Models

### Whisper (Default)

- **Pros**: Robust, well-supported, good general accuracy, handles various accents and languages
- **Cons**: Slower on CPU, requires more VRAM for larger models
- **Best for**: General-purpose transcription, varied audio quality

**Model Sizes**: tiny, base, small, medium, large (recommended: base or small for balance)

### Parakeet V3

- **Pros**: Faster on NVIDIA hardware, better timestamp precision, supports 25 European languages
- **Cons**: Limited to European languages, may struggle with technical vocabulary
- **Best for**: European language content, when speed is important

## API Endpoints

### Profile Management
- `POST /api/profiles` - Create new profile
- `GET /api/profiles` - List all profiles
- `GET /api/profiles/{profile_id}` - Get profile details
- `PUT /api/profiles/{profile_id}` - Update profile
- `DELETE /api/profiles/{profile_id}` - Delete profile

### Conversation Management
- `GET /api/conversations` - List conversations (optional profile_id query param)
- `GET /api/conversations/{conversation_id}` - Get conversation details
- `DELETE /api/conversations/{conversation_id}` - Delete conversation

### File Processing
- `POST /api/upload` - Upload and process audio file
- `GET /api/conversations/{conversation_id}/transcript` - Get transcript
- `GET /api/conversations/{conversation_id}/transcript/segments` - Get transcript segments

### Audio Serving
- `GET /api/audio/{conversation_id}` - Serve audio file for playback

### LLM Operations
- `POST /api/conversations/{conversation_id}/summarize` - Generate summary
- `POST /api/conversations/{conversation_id}/action-items` - Extract action items

### API Key Management
- `POST /api/api-keys` - Create API key (for Ollama/OpenWebUI)
- `GET /api/api-keys` - List API keys
- `GET /api/api-keys/{key_id}` - Get API key metadata
- `DELETE /api/api-keys/{key_id}` - Delete API key

## Troubleshooting

### FFmpeg not found
Ensure FFmpeg is installed and in your PATH. Verify with:
```bash
ffmpeg -version
```

### Model download issues
Whisper models are downloaded automatically on first use. Parakeet V3 requires Hugging Face access. Ensure you have internet connectivity and sufficient disk space.

### Diarization fails
Ensure pyannote-audio is properly installed and you have a valid Hugging Face token if required. Check that `ENABLE_DIARIZATION=true` in your `.env` file.

### LLM operations fail
Verify your OpenWebUI/Ollama endpoint URL is correct and accessible. Ensure you have API keys configured if required.

## Development

### Project Structure

```
listen/
├── main.py                 # Main FastAPI application
├── audio_processor.py      # Audio processing utilities
├── transcriber.py          # Transcription service abstraction
├── transcribers/           # Transcription implementations
│   ├── whisper_transcriber.py
│   └── parakeet_transcriber.py
├── diarization_service.py  # Speaker diarization service
├── llm_service.py          # LLM integration
├── database.py             # Database setup
├── models.py               # SQLAlchemy models
├── config.py               # Configuration
├── schemas.py              # Pydantic schemas
├── templates/              # HTML templates
│   └── index.html
└── static/                 # Static files
    ├── style.css
    └── app.js
```

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]
