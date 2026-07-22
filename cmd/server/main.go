package main

import (
	"log"

	"github.com/jeevansegu/design-a-rate-limiter/internal/server"
)

func main() {
	srv := server.NewServer(":8080")
	log.Printf("Starting server on %s...", srv.Addr)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
