package db

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"

	"listen/internal/migrations"
)

func OpenAndMigrate(sqlitePath string, migrationsDir string) (*sql.DB, error) {
	// modernc sqlite driver uses a DSN like: file:foo.db?_pragma=busy_timeout(5000)
	// Enable foreign keys on every connection
	dsn := fmt.Sprintf("file:%s?_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)", sqlitePath)

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := ping(ctx, db); err != nil {
		_ = db.Close()
		return nil, err
	}

	if err := migrateFromDir(ctx, db, migrationsDir); err != nil {
		_ = db.Close()
		return nil, err
	}

	return db, nil
}

func ping(ctx context.Context, db *sql.DB) error {
	cctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	return db.PingContext(cctx)
}

func migrateFromDir(ctx context.Context, db *sql.DB, migrationsDir string) error {
	migs, err := migrations.ListFromDir(migrationsDir)
	if err != nil {
		return err
	}

	// Ensure migrations table exists (idempotent).
	_, err = db.ExecContext(ctx, `
		PRAGMA foreign_keys = ON;
		CREATE TABLE IF NOT EXISTS schema_migrations (
		  version TEXT NOT NULL PRIMARY KEY,
		  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		);
	`)
	if err != nil {
		return err
	}

	applied := map[string]bool{}
	rows, err := db.QueryContext(ctx, `SELECT version FROM schema_migrations`)
	if err != nil {
		return err
	}
	for rows.Next() {
		var v string
		if err := rows.Scan(&v); err != nil {
			_ = rows.Close()
			return err
		}
		applied[v] = true
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return err
	}
	_ = rows.Close()

	for _, m := range migs {
		if applied[m.Version] {
			continue
		}

		tx, err := db.BeginTx(ctx, nil)
		if err != nil {
			return err
		}

		if _, err := tx.ExecContext(ctx, `PRAGMA foreign_keys = ON;`); err != nil {
			_ = tx.Rollback()
			return err
		}
		if _, err := tx.ExecContext(ctx, m.SQL); err != nil {
			_ = tx.Rollback()
			return fmt.Errorf("apply migration %s: %w", m.Version, err)
		}
		if _, err := tx.ExecContext(ctx, `INSERT INTO schema_migrations(version) VALUES (?)`, m.Version); err != nil {
			_ = tx.Rollback()
			return err
		}
		if err := tx.Commit(); err != nil {
			return err
		}
	}

	return nil
}

