package jobs

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"listen/internal/pipeline"
	"listen/internal/store"
)

type Queue struct {
	store  *store.Store
	logger *log.Logger
	ch     chan Job
	p      *pipeline.Runner
}

type Job struct {
	JobID        int
	ConversationID int
	ProfileID    int
	AudioPath    string
	FileName     string

	GenerateSummary     bool
	GenerateActionItems bool
}

func New(store *store.Store, logger *log.Logger, workerCount int) *Queue {
	q := &Queue{
		store:  store,
		logger: logger,
		ch:     make(chan Job, 128),
	}
	for i := 0; i < workerCount; i++ {
		go q.worker(i + 1)
	}
	return q
}

func NewWithPipeline(store *store.Store, logger *log.Logger, p *pipeline.Runner, workerCount int) *Queue {
	q := &Queue{
		store:  store,
		logger: logger,
		ch:     make(chan Job, 128),
		p:      p,
	}
	for i := 0; i < workerCount; i++ {
		go q.worker(i + 1)
	}
	return q
}

func (q *Queue) Enqueue(j Job) {
	q.ch <- j
}

func (q *Queue) worker(workerID int) {
	for j := range q.ch {
		q.process(workerID, j)
	}
}

func (q *Queue) process(workerID int, j Job) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	q.logger.Printf("job worker=%d job_id=%d conversation_id=%d starting", workerID, j.JobID, j.ConversationID)

	// Move to processing.
	_ = q.store.UpdateJobProgress(ctx, j.JobID, "processing", 10, nil, nil, nil, nil)

	if q.p == nil {
		msg := "pipeline not configured"
		_ = q.store.UpdateJobProgress(ctx, j.JobID, "failed", 100, nil, nil, &msg, nil)
		q.logger.Printf("job worker=%d job_id=%d failed: %s", workerID, j.JobID, msg)
		return
	}

	workDir, err := os.MkdirTemp("", "listen-job-*")
	if err != nil {
		msg := err.Error()
		_ = q.store.UpdateJobProgress(ctx, j.JobID, "failed", 100, nil, nil, &msg, nil)
		return
	}
	defer os.RemoveAll(workDir)

	chunks, err := q.p.ChunkAudio(ctx, j.AudioPath, workDir)
	if err != nil {
		msg := err.Error()
		_ = q.store.UpdateJobProgress(ctx, j.JobID, "failed", 100, nil, nil, &msg, nil)
		q.logger.Printf("job worker=%d job_id=%d chunking failed: %v", workerID, j.JobID, err)
		return
	}
	total := len(chunks)
	_ = q.store.UpdateJobProgress(ctx, j.JobID, "processing", 15, intPtr(total), intPtr(0), nil, nil)

	var combined []pipeline.Segment
	var textParts []string
	var lang *string

	for i, ch := range chunks {
		current := i + 1
		progress := int(15 + (65*current)/max(1, total))
		_ = q.store.UpdateJobProgress(ctx, j.JobID, "processing", progress, nil, intPtr(current), nil, nil)

		outBase := filepath.Join(workDir, fmt.Sprintf("chunk-%03d", current))
		segs, txt, chunkLang, err := q.p.TranscribeChunk(ctx, ch.Path, outBase)
		if err != nil {
			msg := err.Error()
			_ = q.store.UpdateJobProgress(ctx, j.JobID, "failed", 100, nil, intPtr(current), &msg, nil)
			q.logger.Printf("job worker=%d job_id=%d whisper failed: %v", workerID, j.JobID, err)
			return
		}
		if lang == nil && chunkLang != nil && strings.TrimSpace(*chunkLang) != "" {
			lang = chunkLang
		}

		for _, s := range segs {
			combined = append(combined, pipeline.Segment{
				Start: s.Start + ch.Offset,
				End:   s.End + ch.Offset,
				Text:  s.Text,
			})
		}
		if strings.TrimSpace(txt) != "" {
			textParts = append(textParts, strings.TrimSpace(txt))
		}
	}

	_ = q.store.UpdateJobProgress(ctx, j.JobID, "processing", 85, nil, intPtr(total), nil, nil)

	audioURL := "/api/audio/" + fmt.Sprintf("%d", j.ConversationID)
	model := "whisper.cpp"
	transcriptText := strings.Join(textParts, " ")

	inputSegments := make([]store.TranscriptSegmentInput, 0, len(combined))
	for _, s := range combined {
		if strings.TrimSpace(s.Text) == "" {
			continue
		}
		inputSegments = append(inputSegments, store.TranscriptSegmentInput{
			StartTime: s.Start,
			EndTime:   s.End,
			Text:      s.Text,
		})
	}

	transcriptID, err := q.store.CreateTranscriptWithSegments(
		ctx,
		j.ConversationID,
		j.FileName,
		transcriptText,
		nil,
		lang,
		&model,
		audioURL,
		inputSegments,
	)
	if err != nil {
		msg := err.Error()
		_ = q.store.UpdateJobProgress(ctx, j.JobID, "failed", 100, nil, nil, &msg, nil)
		q.logger.Printf("job worker=%d job_id=%d db write failed: %v", workerID, j.JobID, err)
		return
	}

	_ = q.store.UpdateJobProgress(ctx, j.JobID, "completed", 100, nil, intPtr(total), strPtr("success"), &transcriptID)
	q.logger.Printf("job worker=%d job_id=%d completed transcript_id=%d", workerID, j.JobID, transcriptID)
}

func strPtr(s string) *string { return &s }

func intPtr(v int) *int { return &v }

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

