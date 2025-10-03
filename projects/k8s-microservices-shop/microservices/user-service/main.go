package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/redis/go-redis/v9"
	"github.com/sirupsen/logrus"
)

// User represents a user in the system
type User struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
	Name     string `json:"name"`
	Role     string `json:"role"`
	Created  string `json:"created"`
}

// UserService handles user operations
type UserService struct {
	users     map[int]User
	mutex     sync.RWMutex
	redis     *redis.Client
	logger    *logrus.Logger
	requestsTotal *prometheus.CounterVec
	requestDuration *prometheus.HistogramVec
}

// NewUserService creates a new user service
func NewUserService() *UserService {
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})
	logger.SetLevel(logrus.InfoLevel)

	// Initialize Redis client
	redisClient := redis.NewClient(&redis.Options{
		Addr:     getEnv("REDIS_URL", "redis:6379"),
		Password: getEnv("REDIS_PASSWORD", ""),
		DB:       0,
	})

	// Initialize Prometheus metrics
	requestsTotal := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "endpoint", "status"},
	)

	requestDuration := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request duration in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "endpoint"},
	)

	prometheus.MustRegister(requestsTotal, requestDuration)

	service := &UserService{
		users:           make(map[int]User),
		redis:           redisClient,
		logger:          logger,
		requestsTotal:   requestsTotal,
		requestDuration: requestDuration,
	}

	// Initialize with sample data
	service.initializeData()

	return service
}

// initializeData loads sample users
func (us *UserService) initializeData() {
	sampleUsers := []User{
		{ID: 1, Username: "admin", Email: "admin@shop.com", Name: "Administrator", Role: "admin", Created: time.Now().Format(time.RFC3339)},
		{ID: 2, Username: "john_doe", Email: "john@example.com", Name: "John Doe", Role: "customer", Created: time.Now().Format(time.RFC3339)},
		{ID: 3, Username: "jane_smith", Email: "jane@example.com", Name: "Jane Smith", Role: "customer", Created: time.Now().Format(time.RFC3339)},
	}

	for _, user := range sampleUsers {
		us.users[user.ID] = user
	}

	us.logger.Info("Initialized user service with sample data")
}

// Health check handler
func (us *UserService) healthHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	defer func() {
		duration := time.Since(start).Seconds()
		us.requestDuration.WithLabelValues(r.Method, "/health").Observe(duration)
		us.requestsTotal.WithLabelValues(r.Method, "/health", "200").Inc()
	}()

	response := map[string]interface{}{
		"status":    "healthy",
		"service":   "user-service",
		"version":   getEnv("SERVICE_VERSION", "1.0.0"),
		"timestamp": time.Now().Format(time.RFC3339),
		"uptime":    time.Since(startTime).String(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Readiness check handler
func (us *UserService) readyHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	status := "200"
	defer func() {
		duration := time.Since(start).Seconds()
		us.requestDuration.WithLabelValues(r.Method, "/ready").Observe(duration)
		us.requestsTotal.WithLabelValues(r.Method, "/ready", status).Inc()
	}()

	// Check Redis connection
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	_, err := us.redis.Ping(ctx).Result()
	if err != nil {
		status = "503"
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]string{
			"status": "not ready",
			"error":  "Redis connection failed",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
}

// Get all users
func (us *UserService) getUsersHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	status := "200"
	defer func() {
		duration := time.Since(start).Seconds()
		us.requestDuration.WithLabelValues(r.Method, "/users").Observe(duration)
		us.requestsTotal.WithLabelValues(r.Method, "/users", status).Inc()
	}()

	us.mutex.RLock()
	defer us.mutex.RUnlock()

	var userList []User
	for _, user := range us.users {
		userList = append(userList, user)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(userList)

	us.logger.WithFields(logrus.Fields{
		"method": r.Method,
		"path":   r.URL.Path,
		"count":  len(userList),
	}).Info("Retrieved users")
}

// Get user by ID
func (us *UserService) getUserHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	status := "200"
	defer func() {
		duration := time.Since(start).Seconds()
		us.requestDuration.WithLabelValues(r.Method, "/users/{id}").Observe(duration)
		us.requestsTotal.WithLabelValues(r.Method, "/users/{id}", status).Inc()
	}()

	vars := mux.Vars(r)
	idStr := vars["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		status = "400"
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid user ID"})
		return
	}

	us.mutex.RLock()
	user, exists := us.users[id]
	us.mutex.RUnlock()

	if !exists {
		status = "404"
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "User not found"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)

	us.logger.WithFields(logrus.Fields{
		"method":  r.Method,
		"path":    r.URL.Path,
		"user_id": id,
	}).Info("Retrieved user")
}

// Create user
func (us *UserService) createUserHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	status := "201"
	defer func() {
		duration := time.Since(start).Seconds()
		us.requestDuration.WithLabelValues(r.Method, "/users").Observe(duration)
		us.requestsTotal.WithLabelValues(r.Method, "/users", status).Inc()
	}()

	var user User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		status = "400"
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid JSON"})
		return
	}

	us.mutex.Lock()
	// Generate new ID
	maxID := 0
	for id := range us.users {
		if id > maxID {
			maxID = id
		}
	}
	user.ID = maxID + 1
	user.Created = time.Now().Format(time.RFC3339)
	us.users[user.ID] = user
	us.mutex.Unlock()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(user)

	us.logger.WithFields(logrus.Fields{
		"method":   r.Method,
		"path":     r.URL.Path,
		"user_id":  user.ID,
		"username": user.Username,
	}).Info("Created user")
}

// Middleware for logging and metrics
func (us *UserService) loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		
		us.logger.WithFields(logrus.Fields{
			"method": r.Method,
			"path":   r.URL.Path,
			"ip":     r.RemoteAddr,
		}).Info("Request started")

		next.ServeHTTP(w, r)

		us.logger.WithFields(logrus.Fields{
			"method":   r.Method,
			"path":     r.URL.Path,
			"duration": time.Since(start).String(),
		}).Info("Request completed")
	})
}

// CORS middleware
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

var startTime time.Time

func init() {
	startTime = time.Now()
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	userService := NewUserService()

	router := mux.NewRouter()

	// Apply middleware
	router.Use(userService.loggingMiddleware)
	router.Use(corsMiddleware)

	// Health endpoints
	router.HandleFunc("/health", userService.healthHandler).Methods("GET")
	router.HandleFunc("/ready", userService.readyHandler).Methods("GET")
	router.Handle("/metrics", promhttp.Handler())

	// API endpoints
	router.HandleFunc("/users", userService.getUsersHandler).Methods("GET")
	router.HandleFunc("/users/{id:[0-9]+}", userService.getUserHandler).Methods("GET")
	router.HandleFunc("/users", userService.createUserHandler).Methods("POST")

	port := getEnv("PORT", "8080")
	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		userService.logger.WithField("port", port).Info("User service starting")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server startup failed: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	userService.logger.Info("Shutting down server...")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server shutdown failed: %v", err)
	}

	userService.logger.Info("Server shutdown complete")
}