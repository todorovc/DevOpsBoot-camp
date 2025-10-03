FROM golang:1.21-alpine AS builder

# Install git and ca-certificates (needed to clone repositories and verify SSL connections)
RUN apk update && apk add --no-cache git ca-certificates tzdata && update-ca-certificates

# Create appuser for security
RUN adduser -D -g '' appuser

WORKDIR /build

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary with optimizations
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags='-w -s -extldflags "-static"' \
    -a -installsuffix cgo -o user-service .

# Final stage - create minimal image
FROM scratch

# Import CA certificates and timezone data
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Import user and group files
COPY --from=builder /etc/passwd /etc/passwd

# Copy binary
COPY --from=builder /build/user-service /go/bin/user-service

# Use non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/go/bin/user-service", "-healthcheck"]

# Expose port
EXPOSE 8080

# Run the binary
ENTRYPOINT ["/go/bin/user-service"]