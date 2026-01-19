## Listen (v2) — queued Whisper transcription + optional LLM summaries

Fresh rewrite designed to run as **multiple small containers** (no Kubernetes manifests in this repo):

- **frontend**: upload UI + library + rename + prompts editor
- **api**: FastAPI REST API for uploads/jobs/prompts and serving results
- **worker**: Celery worker that runs the ffmpeg + faster-whisper pipeline and optional OpenWebUI calls
- **rabbitmq**: job broker

### Quick start (Docker Compose)

1. Copy env file and edit as needed:

```bash
cp env.example .env
```

2. Build images (Podman):

```bash
podman build -t listen-api:dev ./backend
podman build -t listen-worker:dev -f ./backend/Dockerfile.worker ./backend
podman build -t listen-frontend:dev ./frontend
```

3. Start services:

```bash
podman compose up -d
```

3. Open:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000/docs`

### Configuration

Key env vars (see `env.example`):

- **Broker**: `RABBITMQ_URL`
- **Storage**: `DATABASE_URL`, `UPLOAD_DIR`
- **Whisper**: `WHISPER_MODEL`, `AUDIO_CHUNK_SECONDS`
- **OpenWebUI**: `OPENWEBUI_URL`, `OPENWEBUI_API_KEY`, `OPENWEBUI_DEFAULT_MODEL`

### GPU support

This MVP uses `faster-whisper`. If the worker container has CUDA-capable wheels + runtime available, it will attempt GPU and fall back to CPU.

### Notes

- This repository intentionally contains **no Kubernetes manifests**. The layout is designed to map cleanly onto separate Deployments later.

