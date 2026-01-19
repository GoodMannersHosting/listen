FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# System deps: ffmpeg for audio processing
RUN apk add --no-cache \
    ffmpeg \
    ca-certificates \
  && true

WORKDIR /app

COPY requirements.api.txt /app/requirements.api.txt
RUN pip install --no-cache-dir -r /app/requirements.api.txt

COPY app /app/app
COPY worker /app/worker
COPY prompts /app/prompts

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

