package http

import (
	"database/sql"
	"encoding/json"
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"

	"listen/internal/config"
	"listen/internal/jobs"
	"listen/internal/pipeline"
	"listen/internal/store"
)

func New(cfg config.Config, db *sql.DB, logger *log.Logger) http.Handler {
	r := chi.NewRouter()

	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Compress(5))
	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	r.Get("/healthz", func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})

	// Static assets (existing Svelte build output under ./static).
	staticFS := http.FileServer(http.Dir(cfg.StaticDir))
	r.Mount("/static", http.StripPrefix("/static", staticFS))

	// Root HTML (inject CSS if present).
	r.Get("/", func(w http.ResponseWriter, req *http.Request) {
		serveIndexHTML(w, cfg)
	})

	// Ensure upload dir exists.
	_ = os.MkdirAll(cfg.UploadDir, 0o755)

	st := store.New(db)

	whisperPath := cfg.WhisperPath
	if strings.TrimSpace(whisperPath) == "" {
		whisperPath = firstOnPath(
			"whisper-cli",
			"whisper.cpp",
			"whisper-cpp",
			"whisper",
		)
	}
	if whisperPath == "" {
		whisperPath = "whisper"
		logger.Printf("warn: WHISPER_PATH not set and no whisper binary found on PATH; jobs will fail until configured")
	}
	if strings.TrimSpace(cfg.WhisperModelPath) == "" {
		logger.Printf("warn: WHISPER_MODEL_PATH not set; jobs will fail until configured")
	}

	p := &pipeline.Runner{
		FFmpegPath:       cfg.FFmpegPath,
		WhisperPath:      whisperPath,
		WhisperModelPath: cfg.WhisperModelPath,
		ChunkSeconds:     cfg.AudioChunkDurationS,
		Logger:           logger,
	}
	q := jobs.NewWithPipeline(st, logger, p, 2)

	// API routes (match what the current Svelte UI calls).
	r.Route("/api", func(api chi.Router) {
		api.Get("/profiles", func(w http.ResponseWriter, req *http.Request) {
			list, err := st.ListProfiles(req.Context())
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, list)
		})

		api.Post("/profiles", func(w http.ResponseWriter, req *http.Request) {
			var body struct {
				Name        string  `json:"name"`
				DisplayName *string `json:"display_name"`
			}
			if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid json")
				return
			}
			body.Name = strings.TrimSpace(body.Name)
			if body.Name == "" {
				writeJSONError(w, http.StatusBadRequest, "name is required")
				return
			}
			if body.DisplayName != nil {
				v := strings.TrimSpace(*body.DisplayName)
				body.DisplayName = &v
				if v == "" {
					body.DisplayName = nil
				}
			}

			p, err := st.CreateProfile(req.Context(), body.Name, body.DisplayName)
			if err != nil {
				// Likely UNIQUE constraint violation; keep it simple.
				writeJSONError(w, http.StatusBadRequest, "Profile with this name already exists")
				return
			}
			writeJSON(w, http.StatusCreated, p)
		})

		api.Get("/conversations", func(w http.ResponseWriter, req *http.Request) {
			var profileID *int
			if v := strings.TrimSpace(req.URL.Query().Get("profile_id")); v != "" {
				if id, err := strconv.Atoi(v); err == nil {
					profileID = &id
				}
			}
			list, err := st.ListConversations(req.Context(), profileID)
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, list)
		})

		api.Get("/conversations/{conversationID}", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			conv, err := st.GetConversationDetail(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Conversation not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			_ = st.TouchProfile(req.Context(), conv.ProfileID)
			writeJSON(w, http.StatusOK, conv)
		})

		api.Put("/conversations/{conversationID}", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			var body struct {
				Title *string `json:"title"`
			}
			if err := json.NewDecoder(req.Body).Decode(&body); err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid json")
				return
			}
			if body.Title == nil || strings.TrimSpace(*body.Title) == "" {
				writeJSONError(w, http.StatusBadRequest, "title is required")
				return
			}
			title := strings.TrimSpace(*body.Title)
			updated, err := st.UpdateConversationTitle(req.Context(), id, title)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Conversation not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, updated)
		})

		api.Delete("/conversations/{conversationID}", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			audioPath, err := st.DeleteConversation(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					w.WriteHeader(http.StatusNoContent)
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			// Best-effort file cleanup.
			if audioPath != "" {
				_ = os.Remove(audioPath)
				_ = os.RemoveAll(filepath.Dir(audioPath))
			}
			w.WriteHeader(http.StatusNoContent)
		})

		api.Post("/upload", func(w http.ResponseWriter, req *http.Request) {
			if err := req.ParseMultipartForm(64 << 20); err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid multipart form")
				return
			}
			f, fh, err := req.FormFile("file")
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "file is required")
				return
			}
			defer f.Close()

			fileName := fh.Filename
			if strings.TrimSpace(fileName) == "" {
				writeJSONError(w, http.StatusBadRequest, "No filename provided")
				return
			}
			ext := strings.ToLower(filepath.Ext(fileName))
			allowed := map[string]bool{".mp3": true, ".m4a": true, ".mp4": true, ".ogg": true, ".wav": true, ".flac": true}
			if !allowed[ext] {
				writeJSONError(w, http.StatusBadRequest, "Unsupported file format")
				return
			}

			// Profile: use provided profile_id if possible, otherwise use first active or create default.
			var profileID int
			if v := strings.TrimSpace(req.FormValue("profile_id")); v != "" {
				if id, err := strconv.Atoi(v); err == nil && id > 0 {
					profileID = id
				}
			}
			if profileID == 0 {
				p, err := st.GetFirstActiveProfile(req.Context())
				if err != nil {
					writeJSONError(w, http.StatusInternalServerError, err.Error())
					return
				}
				if p == nil {
					display := "Default Profile"
					created, err := st.CreateProfile(req.Context(), "default", &display)
					if err != nil {
						writeJSONError(w, http.StatusInternalServerError, err.Error())
						return
					}
					profileID = created.ID
				} else {
					profileID = p.ID
				}
			} else {
				if _, err := st.GetProfile(req.Context(), profileID); err != nil {
					writeJSONError(w, http.StatusNotFound, "Profile not found")
					return
				}
			}

			title := fileName
			conv, err := st.CreateConversation(req.Context(), profileID, &title, "")
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}

			profileDir := filepath.Join(cfg.UploadDir, strconv.Itoa(profileID))
			convDir := filepath.Join(profileDir, strconv.Itoa(conv.ID))
			if err := os.MkdirAll(convDir, 0o755); err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}

			audioPath := filepath.Join(convDir, "audio"+ext)
			dst, err := os.Create(audioPath)
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			if _, err := io.Copy(dst, f); err != nil {
				_ = dst.Close()
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			_ = dst.Close()

			_ = st.UpdateConversationAudioPath(req.Context(), conv.ID, audioPath)

			jobID, err := st.CreateJob(req.Context(), conv.ID, "transcription", 5)
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}

			// Options (currently ignored by stub pipeline, but accepted).
			generateSummary := parseBool(req.FormValue("generate_summary"))
			generateActionItems := parseBool(req.FormValue("generate_action_items"))

			q.Enqueue(jobs.Job{
				JobID:         jobID,
				ConversationID: conv.ID,
				ProfileID:     profileID,
				AudioPath:     audioPath,
				FileName:      fileName,
				GenerateSummary:     generateSummary,
				GenerateActionItems: generateActionItems,
			})

			resp := map[string]any{
				"conversation_id": conv.ID,
				"transcript_id":   nil,
				"transcript":      nil,
				"summary":         nil,
				"action_items":    nil,
				"status":          "processing",
				"message":         "Audio upload successful. Processing started. Job ID: " + strconv.Itoa(jobID),
			}
			writeJSON(w, http.StatusOK, resp)
		})

		api.Get("/jobs/{jobID}", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "jobID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid job id")
				return
			}
			job, err := st.GetJobByID(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Job not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, job)
		})

		api.Get("/conversations/{conversationID}/transcript", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			tr, err := st.GetTranscriptByConversationID(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Transcript not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, tr)
		})

		api.Get("/conversations/{conversationID}/job", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			job, err := st.GetLatestJobForConversation(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "No job found for this conversation")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, job)
		})

		api.Get("/conversations/{conversationID}/transcript/segments", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			segs, err := st.ListTranscriptSegmentsByConversationID(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Transcript not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, segs)
		})

		api.Get("/audio/{conversationID}", func(w http.ResponseWriter, req *http.Request) {
			id, err := strconv.Atoi(chi.URLParam(req, "conversationID"))
			if err != nil {
				writeJSONError(w, http.StatusBadRequest, "invalid conversation id")
				return
			}
			conv, err := st.GetConversation(req.Context(), id)
			if err != nil {
				if err == sql.ErrNoRows {
					writeJSONError(w, http.StatusNotFound, "Audio file not found")
					return
				}
				writeJSONError(w, http.StatusInternalServerError, err.Error())
				return
			}
			if strings.TrimSpace(conv.AudioFilePath) == "" {
				writeJSONError(w, http.StatusNotFound, "Audio file not found")
				return
			}
			f, err := os.Open(conv.AudioFilePath)
			if err != nil {
				writeJSONError(w, http.StatusNotFound, "Audio file not found")
				return
			}
			defer f.Close()

			stInfo, err := f.Stat()
			if err != nil {
				writeJSONError(w, http.StatusInternalServerError, "stat failed")
				return
			}

			ctype := mime.TypeByExtension(strings.ToLower(filepath.Ext(conv.AudioFilePath)))
			if ctype == "" {
				ctype = "audio/mpeg"
			}
			w.Header().Set("Content-Type", ctype)
			http.ServeContent(w, req, filepath.Base(conv.AudioFilePath), stInfo.ModTime(), f)
		})
	})

	return r
}

func serveIndexHTML(w http.ResponseWriter, cfg config.Config) {
	b, err := os.ReadFile(cfg.Template)
	if err != nil {
		http.Error(w, "index template not found", http.StatusInternalServerError)
		return
	}
	html := string(b)

	// Mirror the FastAPI behavior: inject a fixed CSS filename if present.
	cssPath := filepath.Join(cfg.StaticDir, "assets", "main.css")
	if fileExists(cssPath) && !strings.Contains(html, "/static/assets/main.css") {
		link := `  <link rel="stylesheet" href="/static/assets/main.css">` + "\n"
		html = strings.Replace(html, "</head>", link+"</head>", 1)
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = io.WriteString(w, html)
}

func fileExists(path string) bool {
	st, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !st.IsDir()
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeJSONError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]any{"detail": detail})
}

func parseBool(v string) bool {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

func firstOnPath(candidates ...string) string {
	for _, c := range candidates {
		if strings.TrimSpace(c) == "" {
			continue
		}
		if p, err := exec.LookPath(c); err == nil && strings.TrimSpace(p) != "" {
			return p
		}
	}
	return ""
}

