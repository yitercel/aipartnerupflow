# API Server Usage Guide

This guide explains how to use the aipartnerupflow API server for remote task execution and integration.

## Overview

The API server provides:
- **A2A Protocol Server**: Standard agent-to-agent communication protocol
- **HTTP API**: RESTful endpoints for task management
- **Real-time Streaming**: Progress updates via SSE/WebSocket
- **Multi-user Support**: User isolation and authentication

## Starting the API Server

### Basic Startup

```bash
# Start server on default port (8000)
aipartnerupflow serve

# Or use the server command
aipartnerupflow-server

# Or use Python module
python -m aipartnerupflow.api.main
```

### Advanced Options

```bash
# Custom host and port
aipartnerupflow serve --host 0.0.0.0 --port 8080

# Enable auto-reload (development)
aipartnerupflow serve --reload

# Multiple workers (production)
aipartnerupflow serve --workers 4

# Custom configuration
aipartnerupflow serve --config config.yaml
```

## API Endpoints

### A2A Protocol Endpoints

The API server implements the A2A (Agent-to-Agent) Protocol standard.

#### Get Agent Card

```bash
curl http://localhost:8000/.well-known/agent-card
```

Returns agent capabilities and available skills.

#### Execute Task Tree (A2A Protocol)

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "execute_task_tree",
    "params": {
      "tasks": [
        {
          "id": "task1",
          "name": "my_task",
          "user_id": "user123",
          "inputs": {"key": "value"}
        }
      ]
    },
    "id": "request-123"
  }'
```

### Task Management Endpoints

#### Create Tasks

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks.create",
    "params": {
      "tasks": [...]
    },
    "id": "request-123"
  }'
```

#### Get Task Status

```bash
curl http://localhost:8000/tasks/{task_id}/status
```

#### List Tasks

```bash
curl http://localhost:8000/tasks?user_id=user123
```

## Streaming Support

### Server-Sent Events (SSE)

Connect to streaming endpoint for real-time updates:

```bash
curl -N http://localhost:8000/stream/{task_id}
```

### WebSocket

Connect via WebSocket for bidirectional communication:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Progress:', update.progress);
};
```

## Client Integration

### Python Client Example

```python
import httpx
import json

# Execute task via API
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/",
        json={
            "jsonrpc": "2.0",
            "method": "execute_task_tree",
            "params": {
                "tasks": [
                    {
                        "id": "task1",
                        "name": "my_task",
                        "user_id": "user123",
                        "inputs": {"key": "value"}
                    }
                ]
            },
            "id": "request-123"
        }
    )
    result = response.json()
    print(result)
```

### JavaScript Client Example

```javascript
// Execute task via API
const response = await fetch('http://localhost:8000/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    method: 'execute_task_tree',
    params: {
      tasks: [
        {
          id: 'task1',
          name: 'my_task',
          user_id: 'user123',
          inputs: { key: 'value' }
        }
      ]
    },
    id: 'request-123'
  })
});

const result = await response.json();
console.log(result);
```

## Authentication

### JWT Authentication (Optional)

If authentication is enabled:

```bash
# Get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token
curl -X POST http://localhost:8000/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## Configuration

### Environment Variables

```bash
# Server configuration
export AIPARTNERUPFLOW_HOST=0.0.0.0
export AIPARTNERUPFLOW_PORT=8000

# Database configuration
export AIPARTNERUPFLOW_DATABASE_URL=postgresql://user:pass@localhost/db

# Authentication
export AIPARTNERUPFLOW_JWT_SECRET=your-secret-key
```

### Configuration File

Create `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  url: postgresql://user:pass@localhost/db

auth:
  enabled: true
  jwt_secret: your-secret-key
```

## Production Deployment

### Using Uvicorn Directly

```bash
uvicorn aipartnerupflow.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

### Using Docker

```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install aipartnerupflow[a2a]
CMD ["aipartnerupflow-server", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Systemd

Create `/etc/systemd/system/aipartnerupflow.service`:

```ini
[Unit]
Description=aipartnerupflow API Server
After=network.target

[Service]
Type=simple
User=apflow
WorkingDirectory=/opt/aipartnerupflow
ExecStart=/usr/local/bin/aipartnerupflow-server --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

## Troubleshooting

### Server Won't Start

- Check if port is already in use
- Verify database connection
- Check logs for errors

### Tasks Not Executing

- Verify executor is registered
- Check task name matches executor ID
- Review server logs

### Connection Issues

- Verify firewall settings
- Check network connectivity
- Ensure server is accessible

## Next Steps

- See [HTTP API Reference](../api/http.md) for complete endpoint documentation
- Check [Examples](../examples/basic_task.md) for integration examples

