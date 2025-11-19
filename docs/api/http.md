# API Reference

This document provides a complete reference for the aipartnerupflow API, which implements the **A2A (Agent-to-Agent) Protocol** standard.

## Overview

The aipartnerupflow API server provides:
- **A2A Protocol Server**: Standard agent-to-agent communication protocol
- **Task Management**: Create, read, update, and delete tasks
- **Task Execution**: Execute task trees with dependency management
- **Real-time Streaming**: Progress updates via EventQueue (SSE/WebSocket)
- **JWT Authentication**: Optional token-based authentication

## Base URL

```
http://localhost:8000  # Default development server
```

## Endpoints

### A2A Protocol Endpoints

#### `GET /.well-known/agent-card`

Get the agent card describing the service capabilities.

**Response:**
```json
{
  "name": "aipartnerupflow",
  "description": "Agent workflow orchestration and execution platform",
  "url": "http://localhost:8000",
  "version": "0.1.0",
  "capabilities": {
    "streaming": true,
    "push_notifications": true
  },
  "skills": [
    {
      "id": "execute_task_tree",
      "name": "Execute Task Tree",
      "description": "Execute a complete task tree with multiple tasks",
      "tags": ["task", "orchestration", "workflow"]
    }
  ]
}
```

#### `POST /`

Main A2A Protocol RPC endpoint. Handles all A2A protocol requests.

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "execute_task_tree",
  "params": {
    "tasks": [...]
  },
  "id": "request-123"
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": "request-123",
  "result": {
    "status": "completed",
    "root_task_id": "task-abc-123",
    "progress": 1.0
  }
}
```

### Task Management Endpoints

#### `POST /tasks`

Task management endpoint. Supports multiple task operations via JSON-RPC 2.0 format.

**Request Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.create",
  "params": {
    "tasks": [
      {
        "id": "task1",
        "name": "Task 1",
        "user_id": "user123",
        "schemas": {
          "method": "executor_id"
        },
        "inputs": {
          "key": "value"
        }
      }
    ]
  },
  "id": "request-123"
}
```

## Task Management Methods

All task management methods use the `/tasks` endpoint with JSON-RPC 2.0 format.

### `tasks.create`

Create one or more tasks and execute them.

**Method:** `tasks.create`

**Parameters:**
- `tasks` (array, required): Array of task objects, or single task object (will be converted to array)

**Task Object Fields:**
- `id` (string, optional): Task ID. If not provided, auto-generated UUID will be used
- `name` (string, required): Task name
- `user_id` (string, optional): User ID for multi-user scenarios
- `parent_id` (string, optional): Parent task ID for task tree structure
- `priority` (integer, optional): Priority level (0=urgent, 1=high, 2=normal, 3=low). Default: 1
- `dependencies` (array, optional): Dependency list. Format: `[{"id": "task-id", "required": true}]`
- `inputs` (object, optional): Execution-time input parameters
- `schemas` (object, optional): Task schemas. Must include `method` field with executor ID
- `params` (object, optional): Executor initialization parameters
- Custom fields: Any additional fields supported by your TaskModel

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.create",
  "params": [
    {
      "id": "root",
      "name": "Root Task",
      "user_id": "user123",
      "schemas": {
        "method": "my_executor"
      },
      "inputs": {
        "data": "test"
      }
    },
    {
      "id": "child",
      "name": "Child Task",
      "user_id": "user123",
      "parent_id": "root",
      "schemas": {
        "method": "another_executor"
      },
      "inputs": {}
    }
  ],
  "id": "create-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "create-request-1",
  "result": {
    "status": "completed",
    "root_task_id": "root",
    "progress": 1.0,
    "task_count": 2
  }
}
```

### `tasks.get`

Get task details by ID.

**Method:** `tasks.get`

**Parameters:**
- `task_id` (string, required): Task ID to retrieve

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.get",
  "params": {
    "task_id": "task-abc-123"
  },
  "id": "get-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "get-request-1",
  "result": {
    "id": "task-abc-123",
    "name": "Task 1",
    "status": "completed",
    "progress": 1.0,
    "inputs": {...},
    "result": {...},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z"
  }
}
```

### `tasks.update`

Update task properties.

**Method:** `tasks.update`

**Parameters:**
- `task_id` (string, required): Task ID to update
- `status` (string, optional): New status
- `inputs` (object, optional): Updated input parameters
- `result` (object, optional): Updated result
- `error` (string, optional): Error message
- `progress` (float, optional): Progress (0.0 to 1.0)
- `started_at` (string, optional): Start timestamp (ISO format)
- `completed_at` (string, optional): Completion timestamp (ISO format)

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.update",
  "params": {
    "task_id": "task-abc-123",
    "status": "in_progress",
    "progress": 0.5
  },
  "id": "update-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "update-request-1",
  "result": {
    "id": "task-abc-123",
    "status": "in_progress",
    "progress": 0.5,
    ...
  }
}
```

### `tasks.delete`

Delete a task (marks as deleted).

**Method:** `tasks.delete`

**Parameters:**
- `task_id` (string, required): Task ID to delete

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.delete",
  "params": {
    "task_id": "task-abc-123"
  },
  "id": "delete-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "delete-request-1",
  "result": {
    "success": true,
    "task_id": "task-abc-123"
  }
}
```

### `tasks.detail`

Get detailed task information (same as `tasks.get`).

**Method:** `tasks.detail`

**Parameters:**
- `task_id` (string, required): Task ID

### `tasks.tree`

Get task tree structure starting from a task.

**Method:** `tasks.tree`

**Parameters:**
- `task_id` (string, optional): Task ID (will find root if task has parent)
- `root_id` (string, optional): Alternative to `task_id`

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.tree",
  "params": {
    "task_id": "child-task-id"
  },
  "id": "tree-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "tree-request-1",
  "result": {
    "id": "root-task-id",
    "name": "Root Task",
    "children": [
      {
        "id": "child-task-id",
        "name": "Child Task",
        "children": []
      }
    ]
  }
}
```

### `tasks.running.list`

List currently running tasks.

**Method:** `tasks.running.list`

**Parameters:**
- `user_id` (string, optional): Filter by user ID
- `limit` (integer, optional): Maximum number of tasks to return (default: 100)

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.running.list",
  "params": {
    "user_id": "user123",
    "limit": 50
  },
  "id": "list-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "list-request-1",
  "result": [
    {
      "id": "task-1",
      "name": "Task 1",
      "status": "in_progress",
      "progress": 0.3
    },
    {
      "id": "task-2",
      "name": "Task 2",
      "status": "in_progress",
      "progress": 0.7
    }
  ]
}
```

### `tasks.running.status`

Get status of one or more running tasks.

**Method:** `tasks.running.status`

**Parameters:**
- `task_ids` (array, required): Array of task IDs to check

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.running.status",
  "params": {
    "task_ids": ["task-1", "task-2"]
  },
  "id": "status-request-1"
}
```

### `tasks.running.count`

Get count of running tasks.

**Method:** `tasks.running.count`

**Parameters:**
- `user_id` (string, optional): Filter by user ID

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.running.count",
  "params": {
    "user_id": "user123"
  },
  "id": "count-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "count-request-1",
  "result": {
    "count": 5,
    "user_id": "user123"
  }
}
```

### `tasks.cancel` / `tasks.running.cancel`

Cancel one or more running tasks.

**Method:** `tasks.cancel` or `tasks.running.cancel`

**Parameters:**
- `task_ids` (array, required): Array of task IDs to cancel
- `force` (boolean, optional): Force immediate cancellation (default: false)

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks.cancel",
  "params": {
    "task_ids": ["task-1", "task-2"],
    "force": false
  },
  "id": "cancel-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "cancel-request-1",
  "result": [
    {
      "task_id": "task-1",
      "status": "cancelled",
      "message": "Task cancelled successfully"
    },
    {
      "task_id": "task-2",
      "status": "cancelled",
      "message": "Task cancelled successfully"
    }
  ]
}
```

## System Endpoints

### `POST /system`

System operations endpoint.

#### `system.health`

Check system health status.

**Method:** `system.health`

**Parameters:** None

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "system.health",
  "params": {},
  "id": "health-request-1"
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "health-request-1",
  "result": {
    "status": "healthy",
    "version": "0.1.0",
    "uptime": 3600
  }
}
```

## Authentication

### JWT Authentication

The API supports optional JWT authentication. To enable:

1. Set environment variable `AIPARTNERUPFLOW_JWT_SECRET_KEY`
2. Include JWT token in request headers: `Authorization: Bearer <token>`

**Token Format:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Payload:**
```json
{
  "user_id": "user123",
  "roles": ["admin"],
  "exp": 1234567890
}
```

**Permission Checking:**
- If `roles` contains `"admin"`, user can access any task
- Otherwise, user can only access tasks with matching `user_id`
- If no `user_id` in token, permission checking is skipped

## Error Responses

All endpoints return JSON-RPC 2.0 error format on failure:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "Error details"
  }
}
```

**Error Codes:**
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32000`: Server error (custom)

## Streaming Support

The API supports real-time progress updates via A2A Protocol's EventQueue:

- **SSE (Server-Sent Events)**: `/events` endpoint
- **WebSocket**: `ws://localhost:8000/ws`

**Event Format:**
```json
{
  "type": "task_progress",
  "task_id": "task-abc-123",
  "data": {
    "progress": 0.5,
    "status": "in_progress"
  }
}
```

## Examples

### Complete Example: Create and Execute Task Tree

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks.create",
    "params": [
      {
        "id": "root",
        "name": "Root Task",
        "user_id": "user123",
        "schemas": {"method": "my_executor"},
        "inputs": {"data": "test"}
      },
      {
        "id": "child",
        "name": "Child Task",
        "user_id": "user123",
        "parent_id": "root",
        "schemas": {"method": "another_executor"},
        "inputs": {}
      }
    ],
    "id": "1"
  }'
```

### Example with Authentication

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks.get",
    "params": {
      "task_id": "task-abc-123"
    },
    "id": "2"
  }'
```

## See Also

- [A2A Protocol Specification](https://github.com/aipartnerup/a2a-protocol)
- [CLI Usage Guide](../guides/cli.md)
- [Architecture Documentation](../architecture/overview.md)

