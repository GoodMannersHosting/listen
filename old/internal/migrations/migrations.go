package migrations

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type Migration struct {
	Version string
	SQL     string
}

func ListFromDir(dir string) ([]Migration, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var names []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if strings.HasSuffix(strings.ToLower(e.Name()), ".sql") {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)

	out := make([]Migration, 0, len(names))
	for _, name := range names {
		b, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return nil, err
		}
		out = append(out, Migration{
			Version: name,
			SQL:     string(b),
		})
	}
	return out, nil
}

