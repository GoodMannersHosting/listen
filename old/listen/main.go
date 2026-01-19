package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"listen/internal/config"
	"listen/internal/db"
	httprouter "listen/internal/http"
)

func main() {
	cfg := config.FromEnv()

	logger := log.New(os.Stdout, "", log.LstdFlags)
	logger.Printf("listen-go starting (addr=%s db=%s upload_dir=%s)", cfg.Addr, cfg.SQLitePath, cfg.UploadDir)

	database, err := db.OpenAndMigrate(cfg.SQLitePath, cfg.MigrationsDir)
	if err != nil {
		logger.Fatalf("db init failed: %v", err)
	}
	defer database.Close()

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           httprouter.New(cfg, database, logger),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		logger.Printf("http listening on %s", cfg.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatalf("http server error: %v", err)
		}
	}()

	// Graceful shutdown.
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	logger.Printf("shutting down")
	if err := srv.Shutdown(ctx); err != nil {
		logger.Printf("shutdown error: %v", err)
	}
}

