package pipeline

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Runner struct {
	FFmpegPath       string
	WhisperPath      string
	WhisperModelPath string
	ChunkSeconds     int
	Logger           *log.Logger
}

type Chunk struct {
	Path   string
	Offset float64 // seconds
	Index  int     // 1-based
}

type Segment struct {
	Start float64
	End   float64
	Text  string
}

type Result struct {
	Language *string
	Text     string
	Segments []Segment
	Duration *float64
}

func (r *Runner) Run(ctx context.Context, inputAudioPath string) (chunks []Chunk, result Result, err error) {
	if r.ChunkSeconds <= 0 {
		return nil, Result{}, errors.New("invalid chunk seconds")
	}
	if strings.TrimSpace(r.FFmpegPath) == "" {
		return nil, Result{}, errors.New("FFmpegPath is required")
	}
	if strings.TrimSpace(r.WhisperPath) == "" {
		return nil, Result{}, errors.New("WhisperPath is required")
	}
	if strings.TrimSpace(r.WhisperModelPath) == "" {
		return nil, Result{}, errors.New("WhisperModelPath is required")
	}

	workDir, err := os.MkdirTemp("", "listen-pipeline-*")
	if err != nil {
		return nil, Result{}, err
	}
	defer os.RemoveAll(workDir)

	chunks, err = r.chunkAudio(ctx, inputAudioPath, workDir)
	if err != nil {
		return nil, Result{}, err
	}
	if len(chunks) == 0 {
		return nil, Result{}, errors.New("no chunks produced")
	}

	var all []Segment
	var parts []string
	var lang *string

	for _, ch := range chunks {
		outBase := filepath.Join(workDir, fmt.Sprintf("whisper-%03d", ch.Index))
		seg, text, chunkLang, err := r.transcribeChunk(ctx, ch.Path, outBase)
		if err != nil {
			return chunks, Result{}, err
		}
		if lang == nil && chunkLang != nil && strings.TrimSpace(*chunkLang) != "" {
			lang = chunkLang
		}

		for _, s := range seg {
			all = append(all, Segment{
				Start: s.Start + ch.Offset,
				End:   s.End + ch.Offset,
				Text:  s.Text,
			})
		}
		if strings.TrimSpace(text) != "" {
			parts = append(parts, strings.TrimSpace(text))
		}
	}

	// Derive duration from the last segment if present.
	var dur *float64
	if len(all) > 0 {
		maxEnd := all[0].End
		for _, s := range all {
			if s.End > maxEnd {
				maxEnd = s.End
			}
		}
		d := maxEnd
		dur = &d
	}

	result = Result{
		Language: lang,
		Text:     strings.Join(parts, " "),
		Segments: all,
		Duration: dur,
	}
	return chunks, result, nil
}

func (r *Runner) ChunkAudio(ctx context.Context, inputAudioPath string, workDir string) ([]Chunk, error) {
	return r.chunkAudio(ctx, inputAudioPath, workDir)
}

func (r *Runner) TranscribeChunk(ctx context.Context, wavPath string, outBase string) (segments []Segment, text string, language *string, err error) {
	return r.transcribeChunk(ctx, wavPath, outBase)
}

func (r *Runner) chunkAudio(ctx context.Context, inputAudioPath string, workDir string) ([]Chunk, error) {
	outPattern := filepath.Join(workDir, "chunk-%03d.wav")
	args := []string{
		"-hide_banner",
		"-loglevel", "error",
		"-i", inputAudioPath,
		"-ac", "1",
		"-ar", "16000",
		"-vn",
		"-f", "segment",
		"-segment_time", strconv.Itoa(r.ChunkSeconds),
		"-reset_timestamps", "1",
		outPattern,
	}
	if err := r.runCmd(ctx, r.FFmpegPath, args...); err != nil {
		return nil, fmt.Errorf("ffmpeg chunking failed: %w", err)
	}

	matches, err := filepath.Glob(filepath.Join(workDir, "chunk-*.wav"))
	if err != nil {
		return nil, err
	}
	sort.Strings(matches)

	var out []Chunk
	for i, p := range matches {
		idx := i + 1
		offset := float64(i * r.ChunkSeconds)
		out = append(out, Chunk{Path: p, Offset: offset, Index: idx})
	}
	return out, nil
}

func (r *Runner) transcribeChunk(ctx context.Context, wavPath string, outBase string) (segments []Segment, text string, language *string, err error) {
	// whisper.cpp (main) style flags: -m <model> -f <file> -oj -of <outBase>
	args := []string{
		"-m", r.WhisperModelPath,
		"-f", wavPath,
		"-oj",
		"-of", outBase,
	}
	if err := r.runCmd(ctx, r.WhisperPath, args...); err != nil {
		return nil, "", nil, fmt.Errorf("whisper failed: %w", err)
	}

	jsonPath := outBase + ".json"
	b, err := os.ReadFile(jsonPath)
	if err != nil {
		return nil, "", nil, fmt.Errorf("read whisper json: %w", err)
	}

	segs, t, lang, err := parseWhisperJSON(b)
	if err != nil {
		return nil, "", nil, err
	}
	return segs, t, lang, nil
}

func (r *Runner) runCmd(ctx context.Context, bin string, args ...string) error {
	if r.Logger != nil {
		r.Logger.Printf("exec: %s %s", bin, strings.Join(args, " "))
	}

	cctx, cancel := context.WithTimeout(ctx, 30*time.Minute)
	defer cancel()

	cmd := exec.CommandContext(cctx, bin, args...)
	cmd.Stdout = io.Discard
	cmd.Stderr = io.Discard
	return cmd.Run()
}

// ---- parsing helpers ----

type whisperJSON struct {
	Text         string            `json:"text"`
	Language     string            `json:"language"`
	Result       *whisperResult    `json:"result"`
	Segments     []whisperSeg      `json:"segments"`
	Transcription []whisperSeg     `json:"transcription"`
}

type whisperResult struct {
	Language string `json:"language"`
}

type whisperSeg struct {
	Text string `json:"text"`

	Start *float64 `json:"start"`
	End   *float64 `json:"end"`

	T0 *int `json:"t0"`
	T1 *int `json:"t1"`

	Offsets    *whisperOffsets    `json:"offsets"`
	Timestamps *whisperTimestamps `json:"timestamps"`
	// Some builds have a typo:
	TimeStanps *whisperTimestamps `json:"timestanps"`
}

type whisperOffsets struct {
	From *int `json:"from"`
	To   *int `json:"to"`
}

type whisperTimestamps struct {
	From string `json:"from"`
	To   string `json:"to"`
}

func parseWhisperJSON(b []byte) ([]Segment, string, *string, error) {
	var w whisperJSON
	if err := json.Unmarshal(b, &w); err != nil {
		return nil, "", nil, fmt.Errorf("parse whisper json: %w", err)
	}

	lang := strings.TrimSpace(w.Language)
	if lang == "" && w.Result != nil {
		lang = strings.TrimSpace(w.Result.Language)
	}
	var langPtr *string
	if lang != "" {
		langPtr = &lang
	}

	segs := w.Segments
	if len(segs) == 0 {
		segs = w.Transcription
	}

	out := make([]Segment, 0, len(segs))
	var parts []string

	for _, s := range segs {
		start, end, ok := segTimesSeconds(s)
		if !ok {
			continue
		}
		txt := strings.TrimSpace(s.Text)
		if txt == "" {
			continue
		}
		out = append(out, Segment{Start: start, End: end, Text: txt})
		parts = append(parts, txt)
	}

	text := strings.TrimSpace(w.Text)
	if text == "" {
		text = strings.Join(parts, " ")
	}

	return out, text, langPtr, nil
}

func segTimesSeconds(s whisperSeg) (start float64, end float64, ok bool) {
	if s.Offsets != nil && s.Offsets.From != nil && s.Offsets.To != nil {
		return float64(*s.Offsets.From) / 1000.0, float64(*s.Offsets.To) / 1000.0, true
	}
	if s.Start != nil && s.End != nil {
		return *s.Start, *s.End, true
	}
	if s.T0 != nil && s.T1 != nil {
		// whisper.cpp uses 10ms units for t0/t1.
		return float64(*s.T0) * 0.01, float64(*s.T1) * 0.01, true
	}
	ts := s.Timestamps
	if ts == nil {
		ts = s.TimeStanps
	}
	if ts != nil && ts.From != "" && ts.To != "" {
		a, errA := parseTimestamp(ts.From)
		b, errB := parseTimestamp(ts.To)
		if errA == nil && errB == nil {
			return a, b, true
		}
	}
	return 0, 0, false
}

func parseTimestamp(v string) (float64, error) {
	// Expected: HH:MM:SS.mmm (or HH:MM:SS)
	v = strings.TrimSpace(v)
	parts := strings.Split(v, ":")
	if len(parts) != 3 {
		return 0, fmt.Errorf("bad timestamp: %q", v)
	}
	h, err := strconv.Atoi(parts[0])
	if err != nil {
		return 0, err
	}
	m, err := strconv.Atoi(parts[1])
	if err != nil {
		return 0, err
	}
	secPart := parts[2]
	s, ms := secPart, "0"
	if strings.Contains(secPart, ".") {
		split := strings.SplitN(secPart, ".", 2)
		s, ms = split[0], split[1]
	}
	sec, err := strconv.Atoi(s)
	if err != nil {
		return 0, err
	}
	ms = strings.TrimRight(ms, "Z") // defensive
	msInt := 0
	if ms != "" {
		// normalize to milliseconds precision
		if len(ms) > 3 {
			ms = ms[:3]
		}
		for len(ms) < 3 {
			ms += "0"
		}
		msInt, _ = strconv.Atoi(ms)
	}
	total := float64(h*3600+m*60+sec) + float64(msInt)/1000.0
	return total, nil
}

