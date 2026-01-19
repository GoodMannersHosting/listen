package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

type Store struct {
	DB *sql.DB
}

func New(db *sql.DB) *Store {
	return &Store{DB: db}
}

type Profile struct {
	ID             int     `json:"id"`
	Name           string  `json:"name"`
	DisplayName    *string `json:"display_name"`
	CreatedAt      string  `json:"created_at"`
	LastAccessedAt string  `json:"last_accessed_at"`
	IsActive       bool    `json:"is_active"`
}

type Conversation struct {
	ID           int     `json:"id"`
	ProfileID    int     `json:"profile_id"`
	Title        *string `json:"title"`
	AudioFilePath string `json:"audio_file_path"`
	CreatedAt    string  `json:"created_at"`
	UpdatedAt    string  `json:"updated_at"`
}

type Transcript struct {
	ID                int              `json:"id"`
	ConversationID     int              `json:"conversation_id"`
	FileName           string           `json:"file_name"`
	TranscriptText     string           `json:"transcript_text"`
	Duration           *float64         `json:"duration"`
	Language           *string          `json:"language"`
	TranscriptionModel *string          `json:"transcription_model"`
	Summary            *string          `json:"summary"`
	ActionItems        json.RawMessage  `json:"action_items"`
	AudioFileURL       *string          `json:"audio_file_url"`
	CreatedAt          string           `json:"created_at"`
	UpdatedAt          string           `json:"updated_at"`
}

type ConversationDetail struct {
	Conversation
	Transcript *Transcript `json:"transcript"`
}

type TranscriptSegment struct {
	ID          int      `json:"id"`
	StartTime   float64  `json:"start_time"`
	EndTime     float64  `json:"end_time"`
	Text        string   `json:"text"`
	SpeakerLabel *string `json:"speaker_label"`
	Confidence  *float64 `json:"confidence"`
}

type ProcessingJob struct {
	ID           int            `json:"job_id"`
	Status       string         `json:"status"`
	Progress     int            `json:"progress"`
	TotalChunks  *int           `json:"total_chunks"`
	CurrentChunk *int           `json:"current_chunk"`
	ConversationID *int         `json:"conversation_id"`
	TranscriptID  *int          `json:"transcript_id"`
	Message      *string        `json:"message"`
	Error        *string        `json:"error"`
}

func (s *Store) ListProfiles(ctx context.Context) ([]Profile, error) {
	rows, err := s.DB.QueryContext(ctx, `
		SELECT id, name, display_name, created_at, last_accessed_at, is_active
		FROM profiles
		WHERE is_active = 1
		ORDER BY id ASC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []Profile
	for rows.Next() {
		var p Profile
		var display sql.NullString
		var created, last string
		var isActiveInt int
		if err := rows.Scan(&p.ID, &p.Name, &display, &created, &last, &isActiveInt); err != nil {
			return nil, err
		}
		if display.Valid {
			p.DisplayName = &display.String
		}
		p.CreatedAt = normalizeSQLiteTime(created)
		p.LastAccessedAt = normalizeSQLiteTime(last)
		p.IsActive = isActiveInt != 0
		out = append(out, p)
	}
	return out, rows.Err()
}

func (s *Store) CreateProfile(ctx context.Context, name string, displayName *string) (Profile, error) {
	res, err := s.DB.ExecContext(ctx, `
		INSERT INTO profiles(name, display_name) VALUES (?, ?)
	`, name, nullableString(displayName))
	if err != nil {
		return Profile{}, err
	}
	id64, err := res.LastInsertId()
	if err != nil {
		return Profile{}, err
	}
	return s.GetProfile(ctx, int(id64))
}

func (s *Store) GetProfile(ctx context.Context, id int) (Profile, error) {
	var p Profile
	var display sql.NullString
	var created, last string
	var isActiveInt int
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, name, display_name, created_at, last_accessed_at, is_active
		FROM profiles
		WHERE id = ?
	`, id).Scan(&p.ID, &p.Name, &display, &created, &last, &isActiveInt)
	if err != nil {
		return Profile{}, err
	}
	if display.Valid {
		p.DisplayName = &display.String
	}
	p.CreatedAt = normalizeSQLiteTime(created)
	p.LastAccessedAt = normalizeSQLiteTime(last)
	p.IsActive = isActiveInt != 0
	return p, nil
}

func (s *Store) GetFirstActiveProfile(ctx context.Context) (*Profile, error) {
	var p Profile
	var display sql.NullString
	var created, last string
	var isActiveInt int
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, name, display_name, created_at, last_accessed_at, is_active
		FROM profiles
		WHERE is_active = 1
		ORDER BY id ASC
		LIMIT 1
	`).Scan(&p.ID, &p.Name, &display, &created, &last, &isActiveInt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if display.Valid {
		p.DisplayName = &display.String
	}
	p.CreatedAt = normalizeSQLiteTime(created)
	p.LastAccessedAt = normalizeSQLiteTime(last)
	p.IsActive = isActiveInt != 0
	return &p, nil
}

func (s *Store) TouchProfile(ctx context.Context, id int) error {
	_, err := s.DB.ExecContext(ctx, `
		UPDATE profiles SET last_accessed_at = CURRENT_TIMESTAMP WHERE id = ?
	`, id)
	return err
}

func (s *Store) ListConversations(ctx context.Context, profileID *int) ([]Conversation, error) {
	var rows *sql.Rows
	var err error
	if profileID != nil {
		rows, err = s.DB.QueryContext(ctx, `
			SELECT id, profile_id, title, audio_file_path, created_at, updated_at
			FROM conversations
			WHERE profile_id = ?
			ORDER BY created_at DESC
		`, *profileID)
	} else {
		rows, err = s.DB.QueryContext(ctx, `
			SELECT id, profile_id, title, audio_file_path, created_at, updated_at
			FROM conversations
			ORDER BY created_at DESC
		`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []Conversation
	for rows.Next() {
		var c Conversation
		var title sql.NullString
		var created, updated string
		if err := rows.Scan(&c.ID, &c.ProfileID, &title, &c.AudioFilePath, &created, &updated); err != nil {
			return nil, err
		}
		if title.Valid {
			c.Title = &title.String
		}
		c.CreatedAt = normalizeSQLiteTime(created)
		c.UpdatedAt = normalizeSQLiteTime(updated)
		out = append(out, c)
	}
	return out, rows.Err()
}

func (s *Store) CreateConversation(ctx context.Context, profileID int, title *string, audioPath string) (Conversation, error) {
	res, err := s.DB.ExecContext(ctx, `
		INSERT INTO conversations(profile_id, title, audio_file_path) VALUES (?, ?, ?)
	`, profileID, nullableString(title), audioPath)
	if err != nil {
		return Conversation{}, err
	}
	id64, err := res.LastInsertId()
	if err != nil {
		return Conversation{}, err
	}
	return s.GetConversation(ctx, int(id64))
}

func (s *Store) UpdateConversationAudioPath(ctx context.Context, conversationID int, audioPath string) error {
	_, err := s.DB.ExecContext(ctx, `
		UPDATE conversations
		SET audio_file_path = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
	`, audioPath, conversationID)
	return err
}

func (s *Store) GetConversation(ctx context.Context, id int) (Conversation, error) {
	var c Conversation
	var title sql.NullString
	var created, updated string
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, profile_id, title, audio_file_path, created_at, updated_at
		FROM conversations
		WHERE id = ?
	`, id).Scan(&c.ID, &c.ProfileID, &title, &c.AudioFilePath, &created, &updated)
	if err != nil {
		return Conversation{}, err
	}
	if title.Valid {
		c.Title = &title.String
	}
	c.CreatedAt = normalizeSQLiteTime(created)
	c.UpdatedAt = normalizeSQLiteTime(updated)
	return c, nil
}

func (s *Store) GetConversationDetail(ctx context.Context, id int) (ConversationDetail, error) {
	conv, err := s.GetConversation(ctx, id)
	if err != nil {
		return ConversationDetail{}, err
	}

	tr, err := s.GetTranscriptByConversationID(ctx, id)
	if errors.Is(err, sql.ErrNoRows) {
		return ConversationDetail{Conversation: conv, Transcript: nil}, nil
	}
	if err != nil {
		return ConversationDetail{}, err
	}
	return ConversationDetail{Conversation: conv, Transcript: &tr}, nil
}

func (s *Store) UpdateConversationTitle(ctx context.Context, id int, title string) (Conversation, error) {
	_, err := s.DB.ExecContext(ctx, `
		UPDATE conversations
		SET title = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
	`, title, id)
	if err != nil {
		return Conversation{}, err
	}
	return s.GetConversation(ctx, id)
}

func (s *Store) DeleteConversation(ctx context.Context, id int) (audioPath string, err error) {
	var p string
	if err := s.DB.QueryRowContext(ctx, `SELECT audio_file_path FROM conversations WHERE id = ?`, id).Scan(&p); err != nil {
		return "", err
	}
	if _, err := s.DB.ExecContext(ctx, `DELETE FROM conversations WHERE id = ?`, id); err != nil {
		return "", err
	}
	return p, nil
}

func (s *Store) GetTranscriptByConversationID(ctx context.Context, conversationID int) (Transcript, error) {
	var tr Transcript
	var duration sql.NullFloat64
	var language, model, summary, audioURL sql.NullString
	var actionItems sql.NullString
	var created, updated string
	err := s.DB.QueryRowContext(ctx, `
		SELECT id, conversation_id, file_name, transcript_text, duration, language, transcription_model,
		       summary, action_items, audio_file_url, created_at, updated_at
		FROM transcripts
		WHERE conversation_id = ?
	`, conversationID).Scan(
		&tr.ID, &tr.ConversationID, &tr.FileName, &tr.TranscriptText, &duration, &language, &model,
		&summary, &actionItems, &audioURL, &created, &updated,
	)
	if err != nil {
		return Transcript{}, err
	}
	if duration.Valid {
		tr.Duration = &duration.Float64
	}
	if language.Valid {
		tr.Language = &language.String
	}
	if model.Valid {
		tr.TranscriptionModel = &model.String
	}
	if summary.Valid {
		tr.Summary = &summary.String
	}
	if audioURL.Valid {
		tr.AudioFileURL = &audioURL.String
	}
	if actionItems.Valid && stringsTrim(actionItems.String) != "" {
		tr.ActionItems = json.RawMessage(actionItems.String)
	} else {
		tr.ActionItems = nil
	}
	tr.CreatedAt = normalizeSQLiteTime(created)
	tr.UpdatedAt = normalizeSQLiteTime(updated)
	return tr, nil
}

func (s *Store) ListTranscriptSegmentsByConversationID(ctx context.Context, conversationID int) ([]TranscriptSegment, error) {
	var transcriptID int
	if err := s.DB.QueryRowContext(ctx, `SELECT id FROM transcripts WHERE conversation_id = ?`, conversationID).Scan(&transcriptID); err != nil {
		return nil, err
	}

	rows, err := s.DB.QueryContext(ctx, `
		SELECT id, start_time, end_time, text, speaker_label, confidence
		FROM transcript_segments
		WHERE transcript_id = ?
		ORDER BY start_time ASC
	`, transcriptID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []TranscriptSegment
	for rows.Next() {
		var seg TranscriptSegment
		var speaker sql.NullString
		var conf sql.NullFloat64
		if err := rows.Scan(&seg.ID, &seg.StartTime, &seg.EndTime, &seg.Text, &speaker, &conf); err != nil {
			return nil, err
		}
		if speaker.Valid {
			seg.SpeakerLabel = &speaker.String
		}
		if conf.Valid {
			seg.Confidence = &conf.Float64
		}
		out = append(out, seg)
	}
	return out, rows.Err()
}

func (s *Store) CreateJob(ctx context.Context, conversationID int, jobType string, initialProgress int) (int, error) {
	res, err := s.DB.ExecContext(ctx, `
		INSERT INTO processing_jobs(conversation_id, job_type, status, progress)
		VALUES (?, ?, 'pending', ?)
	`, conversationID, jobType, initialProgress)
	if err != nil {
		return 0, err
	}
	id64, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}
	return int(id64), nil
}

func (s *Store) GetLatestJobForConversation(ctx context.Context, conversationID int) (ProcessingJob, error) {
	var job ProcessingJob
	var status string
	var progress int
	var total, current sql.NullInt64
	var convID sql.NullInt64
	var transcriptID sql.NullInt64
	var result sql.NullString

	err := s.DB.QueryRowContext(ctx, `
		SELECT id, status, progress, total_chunks, current_chunk, conversation_id, transcript_id, result
		FROM processing_jobs
		WHERE conversation_id = ?
		ORDER BY created_at DESC, id DESC
		LIMIT 1
	`, conversationID).Scan(
		&job.ID, &status, &progress, &total, &current, &convID, &transcriptID, &result,
	)
	if err != nil {
		return ProcessingJob{}, err
	}
	job.Status = status
	job.Progress = progress
	if total.Valid {
		v := int(total.Int64)
		job.TotalChunks = &v
	}
	if current.Valid {
		v := int(current.Int64)
		job.CurrentChunk = &v
	}
	if convID.Valid {
		v := int(convID.Int64)
		job.ConversationID = &v
	}
	if transcriptID.Valid {
		v := int(transcriptID.Int64)
		job.TranscriptID = &v
	}
	if result.Valid && job.Status == "failed" {
		job.Error = &result.String
	}
	msg := fmt.Sprintf("Job status: %s", job.Status)
	job.Message = &msg
	return job, nil
}

func (s *Store) GetJobByID(ctx context.Context, jobID int) (ProcessingJob, error) {
	var job ProcessingJob
	var status string
	var progress int
	var total, current sql.NullInt64
	var convID sql.NullInt64
	var transcriptID sql.NullInt64
	var result sql.NullString

	err := s.DB.QueryRowContext(ctx, `
		SELECT id, status, progress, total_chunks, current_chunk, conversation_id, transcript_id, result
		FROM processing_jobs
		WHERE id = ?
	`, jobID).Scan(
		&job.ID, &status, &progress, &total, &current, &convID, &transcriptID, &result,
	)
	if err != nil {
		return ProcessingJob{}, err
	}
	job.Status = status
	job.Progress = progress
	if total.Valid {
		v := int(total.Int64)
		job.TotalChunks = &v
	}
	if current.Valid {
		v := int(current.Int64)
		job.CurrentChunk = &v
	}
	if convID.Valid {
		v := int(convID.Int64)
		job.ConversationID = &v
	}
	if transcriptID.Valid {
		v := int(transcriptID.Int64)
		job.TranscriptID = &v
	}
	if result.Valid && job.Status == "failed" {
		job.Error = &result.String
	}
	msg := fmt.Sprintf("Job status: %s", job.Status)
	job.Message = &msg
	return job, nil
}

func (s *Store) UpdateJobProgress(ctx context.Context, jobID int, status string, progress int, totalChunks, currentChunk *int, result *string, transcriptID *int) error {
	_, err := s.DB.ExecContext(ctx, `
		UPDATE processing_jobs
		SET status = ?,
		    progress = ?,
		    total_chunks = COALESCE(?, total_chunks),
		    current_chunk = COALESCE(?, current_chunk),
		    result = COALESCE(?, result),
		    transcript_id = COALESCE(?, transcript_id)
		WHERE id = ?
	`, status, progress, nullableInt(totalChunks), nullableInt(currentChunk), nullableString(result), nullableInt(transcriptID), jobID)
	return err
}

func (s *Store) CreateTranscriptForConversation(ctx context.Context, conversationID int, fileName string, transcriptText string, audioURL string) (int, error) {
	res, err := s.DB.ExecContext(ctx, `
		INSERT INTO transcripts(conversation_id, file_name, transcript_text, audio_file_url)
		VALUES (?, ?, ?, ?)
	`, conversationID, fileName, transcriptText, audioURL)
	if err != nil {
		return 0, err
	}
	id64, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}
	return int(id64), nil
}

type TranscriptSegmentInput struct {
	StartTime float64
	EndTime   float64
	Text      string
}

func (s *Store) CreateTranscriptWithSegments(
	ctx context.Context,
	conversationID int,
	fileName string,
	transcriptText string,
	duration *float64,
	language *string,
	model *string,
	audioURL string,
	segments []TranscriptSegmentInput,
) (int, error) {
	tx, err := s.DB.BeginTx(ctx, nil)
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()

	res, err := tx.ExecContext(ctx, `
		INSERT INTO transcripts(
		  conversation_id, file_name, transcript_text, duration, language, transcription_model, audio_file_url
		) VALUES (?, ?, ?, ?, ?, ?, ?)
	`, conversationID, fileName, transcriptText, nullableFloat(duration), nullableString(language), nullableString(model), audioURL)
	if err != nil {
		return 0, err
	}
	id64, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}
	transcriptID := int(id64)

	if len(segments) > 0 {
		stmt, err := tx.PrepareContext(ctx, `
			INSERT INTO transcript_segments(transcript_id, start_time, end_time, text)
			VALUES (?, ?, ?, ?)
		`)
		if err != nil {
			return 0, err
		}
		defer stmt.Close()

		for _, seg := range segments {
			if stringsTrim(seg.Text) == "" {
				continue
			}
			if _, err := stmt.ExecContext(ctx, transcriptID, seg.StartTime, seg.EndTime, seg.Text); err != nil {
				return 0, err
			}
		}
	}

	if err := tx.Commit(); err != nil {
		return 0, err
	}
	return transcriptID, nil
}

func normalizeSQLiteTime(v string) string {
	// SQLite CURRENT_TIMESTAMP is "YYYY-MM-DD HH:MM:SS".
	// The frontend uses `new Date(dateString)` which parses "YYYY-MM-DDTHH:MM:SSZ" reliably.
	// Convert if it looks like the SQLite default.
	if len(v) >= len("2006-01-02 15:04:05") && v[10] == ' ' {
		// Treat as UTC (good enough for UI sorting).
		t, err := time.Parse("2006-01-02 15:04:05", v)
		if err == nil {
			return t.UTC().Format(time.RFC3339)
		}
	}
	return v
}

func stringsTrim(s string) string {
	for len(s) > 0 && (s[0] == ' ' || s[0] == '\n' || s[0] == '\t' || s[0] == '\r') {
		s = s[1:]
	}
	for len(s) > 0 {
		last := s[len(s)-1]
		if last == ' ' || last == '\n' || last == '\t' || last == '\r' {
			s = s[:len(s)-1]
			continue
		}
		break
	}
	return s
}

func nullableString(v *string) any {
	if v == nil {
		return nil
	}
	return *v
}

func nullableInt(v *int) any {
	if v == nil {
		return nil
	}
	return *v
}

func nullableFloat(v *float64) any {
	if v == nil {
		return nil
	}
	return *v
}
