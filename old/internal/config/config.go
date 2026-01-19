package config

import (
	"os"
	"strconv"
	"strings"
)

type Config struct {
	Addr       string
	SQLitePath string
	UploadDir  string
	StaticDir  string
	Template   string
	MigrationsDir string

	FFmpegPath          string
	FFprobePath         string
	WhisperPath         string
	WhisperModelPath    string
	AudioChunkDurationS int
}

func FromEnv() Config {
	addr := getenvDefault("LISTEN_ADDR", ":8000")

	// Compatibility: the Python app uses DATABASE_URL=sqlite:///./listen.db by default.
	sqlitePath := getenvDefault("DATABASE_URL", "sqlite:///./listen.db")
	sqlitePath = normalizeSQLitePath(sqlitePath)

	uploadDir := getenvDefault("UPLOAD_DIR", "./uploads")
	staticDir := getenvDefault("STATIC_DIR", "./static")
	templatePath := getenvDefault("INDEX_TEMPLATE", "./templates/index_svelte.html")
	migrationsDir := getenvDefault("MIGRATIONS_DIR", "./migrations")

	ffmpegPath := getenvDefault("FFMPEG_PATH", "ffmpeg")
	ffprobePath := getenvDefault("FFPROBE_PATH", "ffprobe")
	whisperPath := getenvDefault("WHISPER_PATH", "")
	whisperModelPath := getenvDefault("WHISPER_MODEL_PATH", "")
	audioChunkDurationS := getenvIntDefault("AUDIO_CHUNK_DURATION", 15)

	return Config{
		Addr:       addr,
		SQLitePath: sqlitePath,
		UploadDir:  uploadDir,
		StaticDir:  staticDir,
		Template:   templatePath,
		MigrationsDir: migrationsDir,

		FFmpegPath:          ffmpegPath,
		FFprobePath:         ffprobePath,
		WhisperPath:         whisperPath,
		WhisperModelPath:    whisperModelPath,
		AudioChunkDurationS: audioChunkDurationS,
	}
}

func getenvDefault(key, def string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return def
}

func getenvIntDefault(key string, def int) int {
	v := strings.TrimSpace(os.Getenv(key))
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return def
	}
	return n
}

func normalizeSQLitePath(v string) string {
	v = strings.TrimSpace(v)
	v = strings.TrimPrefix(v, "sqlite:///")
	v = strings.TrimPrefix(v, "sqlite://")
	if v == "" {
		return "./listen.db"
	}
	return v
}

