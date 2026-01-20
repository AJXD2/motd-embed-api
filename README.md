# Minecraft MOTD Embed API

A FastAPI-based web service that generates embeddable HTML for Minecraft server MOTDs (Message of the Day). Fetches live server status, parses Minecraft formatting codes, and generates styled HTML embeds.

## Features

- **Live Server Status**: Queries Minecraft servers in real-time
- **MOTD Parsing**: Converts Minecraft § formatting codes to HTML/CSS
- **Caching**: 30-second cache to reduce server load
- **Embeddable**: Generate HTML embeds for use in websites
- **Docker Support**: Production-ready containerized deployment

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd motd-embed-api
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the API**
   - API: http://localhost:8000
   - Health check: http://localhost:8000/health
   - Embed example: http://localhost:8000/v1/server/mc.hypixel.net/embed

### Using Docker Build

```bash
# Build the image
docker build -t motd-embed-api .

# Run the container
docker run -d \
  -p 8000:8000 \
  --name motd-embed-api \
  -e ALLOWED_ORIGINS="https://example.com" \
  motd-embed-api
```

### Local Development

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Run the development server**
   ```bash
   # With reload enabled
   RELOAD=true uv run motd-embed-api

   # Or use uvicorn directly
   uv run uvicorn motd_embed_api.main:app --reload
   ```

## API Endpoints

### GET `/v1/server/{ip}/embed`

Returns an HTML embed for the specified Minecraft server's MOTD.

**Parameters:**
- `ip` (path): Server address (e.g., `mc.hypixel.net` or `play.example.com:25565`)

**Example:**
```bash
curl http://localhost:8000/v1/server/mc.hypixel.net/embed
```

**Response:** HTML document with formatted MOTD

### GET `/v1/server/{ip}/image`

Placeholder endpoint for future image generation.

**Response:** JSON indicating feature not yet implemented

### GET `/health`

Health check endpoint for monitoring and container orchestration.

**Response:**
```json
{"status": "ok"}
```

## Configuration

Configuration is done via environment variables. See `.env.example` for all options.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host to bind to |
| `PORT` | `8000` | Port to run the server on |
| `RELOAD` | `false` | Enable auto-reload (development only) |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warning, error, critical) |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |

### Production Configuration

For production deployment:

```bash
# Copy example env file
cp .env.example .env

# Edit with production values
nano .env
```

**Important:** Set `ALLOWED_ORIGINS` to specific domains in production:
```env
ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

## Docker Deployment

### Production Deployment

1. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your production settings
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the service**
   ```bash
   docker-compose down
   ```

### Kubernetes Deployment

Example deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: motd-embed-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: motd-embed-api
  template:
    metadata:
      labels:
        app: motd-embed-api
    spec:
      containers:
      - name: api
        image: motd-embed-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ALLOWED_ORIGINS
          value: "https://example.com"
        - name: LOG_LEVEL
          value: "info"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "128Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: motd-embed-api
spec:
  selector:
    app: motd-embed-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Architecture

```
Request → FastAPI → Cache Layer → Server Status Fetcher → MOTD Parser → HTML Generator → Response
```

### Components

- **`main.py`**: FastAPI application and routes
- **`server.py`**: Minecraft server communication via mcstatus
- **`motd_parser.py`**: Converts § formatting codes to HTML
- **`html_generator.py`**: Generates embeddable HTML
- **`cache.py`**: Simple TTL-based caching (30s default)

### Static Assets

The `static/` directory contains:
- `motd-embed.css`: Minecraft-themed styling
- `minecraft-background-dark-160x-K223BAAL.png`: Background texture
- `unknown_server.jpg`: Fallback server icon

## Development

### Project Structure

```
motd-embed-api/
├── src/
│   └── motd_embed_api/
│       ├── __init__.py
│       ├── main.py           # FastAPI app & routes
│       ├── server.py          # Minecraft server queries
│       ├── motd_parser.py     # MOTD formatting parser
│       ├── html_generator.py  # HTML embed generation
│       └── cache.py           # Caching layer
├── static/                    # Static assets (CSS, images)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# TODO: Add tests
pytest
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```

## Security Considerations

- **CORS**: Configure `ALLOWED_ORIGINS` for production
- **Rate Limiting**: Consider adding rate limiting middleware
- **SSRF Protection**: Currently allows connections to any server
- **Input Validation**: IP addresses are validated but not restricted

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
