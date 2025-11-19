# Custom Tasks Guide

This guide explains how to create custom tasks by implementing the `ExecutableTask` interface.

## Overview

Custom tasks allow you to:
- Implement any type of task logic (API calls, data processing, file operations, etc.)
- Integrate with external services
- Create reusable task components
- Extend aipartnerupflow with domain-specific functionality

## ExecutableTask Interface

All custom tasks must implement the `ExecutableTask` interface:

```python
from aipartnerupflow import ExecutableTask
from typing import Dict, Any

class MyCustomTask(ExecutableTask):
    """Your custom task implementation"""
    
    @property
    def id(self) -> str:
        """Unique identifier for this task"""
        return "my_custom_task"
    
    @property
    def name(self) -> str:
        """Display name for this task"""
        return "My Custom Task"
    
    @property
    def description(self) -> str:
        """Description of what this task does"""
        return "Performs custom operations"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task logic"""
        # Your implementation here
        return {"status": "completed", "result": "..."}
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for input parameters"""
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter 1"}
            },
            "required": ["param1"]
        }
```

## Required Methods

### 1. `id` Property

Unique identifier for the task. Used for task registration and references.

```python
@property
def id(self) -> str:
    return "my_task_id"  # Must be unique
```

### 2. `name` Property

Human-readable name for the task.

```python
@property
def name(self) -> str:
    return "My Task Name"
```

### 3. `description` Property

Description of what the task does.

```python
@property
def description(self) -> str:
    return "This task performs specific operations"
```

### 4. `execute()` Method

Main execution logic. Must be async.

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the task
    
    Args:
        inputs: Input parameters from task.inputs
        
    Returns:
        Execution result dictionary
    """
    # Your logic here
    result = perform_operation(inputs)
    return {"status": "completed", "result": result}
```

### 5. `get_input_schema()` Method

Returns JSON Schema defining input parameters.

```python
def get_input_schema(self) -> Dict[str, Any]:
    """
    Return JSON Schema for input parameters
    
    Returns:
        JSON Schema dictionary
    """
    return {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to process"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["url"]
    }
```

## Complete Example: HTTP API Call Task

```python
from aipartnerupflow import ExecutableTask
from typing import Dict, Any
import aiohttp
import asyncio

class APICallTask(ExecutableTask):
    """Task that calls an external HTTP API"""
    
    @property
    def id(self) -> str:
        return "api_call_task"
    
    @property
    def name(self) -> str:
        return "API Call Task"
    
    @property
    def description(self) -> str:
        return "Calls an external HTTP API and returns the response"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call"""
        url = inputs.get("url")
        method = inputs.get("method", "GET")
        headers = inputs.get("headers", {})
        data = inputs.get("data")
        timeout = inputs.get("timeout", 30)
        
        if not url:
            raise ValueError("URL is required")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data if method != "GET" else None,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    result = await response.json() if response.content_type == "application/json" else await response.text()
                    
                    return {
                        "status": "completed",
                        "status_code": response.status,
                        "data": result,
                        "headers": dict(response.headers)
                    }
        except asyncio.TimeoutError:
            return {
                "status": "failed",
                "error": f"Request timeout after {timeout} seconds"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define input parameters"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "API endpoint URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method",
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers"
                },
                "data": {
                    "type": "object",
                    "description": "Request body data"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30
                }
            },
            "required": ["url"]
        }
```

## Registering Custom Tasks

The recommended way to register custom tasks is using the `@executor_register()` decorator:

```python
from aipartnerupflow import BaseTask, executor_register

@executor_register()
class MyCustomTask(BaseTask):
    id = "my_custom_task"
    # ... rest of implementation
```

The decorator automatically registers the task when the class is defined. Simply import the class to make it available:

```python
# Import the executor (automatically registered via @executor_register())
from my_module import MyCustomTask
```

**Note:** For executors that need runtime configuration (like CrewManager), you can register instances directly using `get_registry().register(instance)`, but this is a special case.

### Using Registered Tasks

Once registered, use the task by its `id` in task creation:

```python
task = await task_manager.task_repository.create_task(
    name="my_custom_task",  # Use the task's id
    user_id="user123",
    inputs={
        "param1": "value1",
        "param2": "value2"
    }
)
```

## Input Schema Best Practices

### 1. Use JSON Schema Format

Follow JSON Schema specification for input validation:

```python
def get_input_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "field_name": {
                "type": "string",  # or "integer", "boolean", "array", "object"
                "description": "Field description",
                "default": "default_value"  # Optional default
            }
        },
        "required": ["field_name"]  # List required fields
    }
```

### 2. Provide Default Values

Use defaults for optional parameters:

```python
"timeout": {
    "type": "integer",
    "default": 30,
    "description": "Timeout in seconds"
}
```

### 3. Add Descriptions

Always include descriptions for clarity:

```python
"url": {
    "type": "string",
    "description": "The URL to fetch data from"
}
```

### 4. Use Enums for Limited Choices

Use enum for fields with limited valid values:

```python
"method": {
    "type": "string",
    "enum": ["GET", "POST", "PUT", "DELETE"],
    "description": "HTTP method"
}
```

## Error Handling

### Returning Errors

Return error information in the result:

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = perform_operation(inputs)
        return {"status": "completed", "result": result}
    except ValueError as e:
        return {
            "status": "failed",
            "error": str(e),
            "error_type": "ValueError"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }
```

### Raising Exceptions

You can also raise exceptions (TaskManager will catch them):

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    if not inputs.get("required_param"):
        raise ValueError("required_param is required")
    
    # Continue with execution
    return {"status": "completed", "result": "..."}
```

## Advanced Features

### Optional: Cancellation Support

Implement `cancel()` method for cancellation support:

```python
async def cancel(self) -> Dict[str, Any]:
    """
    Cancel task execution
    
    Returns:
        Cancellation result dictionary
    """
    # Stop any ongoing operations
    self._cancelled = True
    
    return {
        "status": "cancelled",
        "message": "Task cancelled by user",
        "partial_result": self._partial_result if hasattr(self, "_partial_result") else None
    }
```

### Accessing Task Context

Access task information in execute method:

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Note: Task context is available through TaskManager
    # You can access it via hooks or by storing task reference
    
    # Your implementation
    return {"status": "completed"}
```

## Common Patterns

### Pattern 1: Simple Data Processing

```python
class DataProcessingTask(ExecutableTask):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        data = inputs.get("data", [])
        operation = inputs.get("operation", "sum")
        
        if operation == "sum":
            result = sum(data)
        elif operation == "average":
            result = sum(data) / len(data) if data else 0
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {"status": "completed", "result": result}
```

### Pattern 2: File Operations

```python
import aiofiles

class FileReadTask(ExecutableTask):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        file_path = inputs.get("file_path")
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
        
        return {"status": "completed", "content": content}
```

### Pattern 3: Database Operations

```python
class DatabaseQueryTask(ExecutableTask):
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("query")
        params = inputs.get("params", {})
        
        result = await self.db.fetch(query, params)
        
        return {"status": "completed", "rows": result}
```

## Testing Custom Tasks

### Unit Testing

```python
import pytest
from my_tasks import MyCustomTask

@pytest.mark.asyncio
async def test_my_custom_task():
    task = MyCustomTask()
    
    inputs = {
        "param1": "value1",
        "param2": "value2"
    }
    
    result = await task.execute(inputs)
    
    assert result["status"] == "completed"
    assert "result" in result
```

### Integration Testing

```python
from aipartnerupflow import TaskManager, TaskTreeNode, create_session
# Import the executor (automatically registered via @executor_register())
from my_module import MyCustomTask

async def test_task_integration():
    
    # Create and execute
    db = create_session()
    task_manager = TaskManager(db)
    
    task = await task_manager.task_repository.create_task(
        name="my_custom_task",
        user_id="test_user",
        inputs={"param1": "value1"}
    )
    
    task_tree = TaskTreeNode(task)
    result = await task_manager.distribute_task_tree(task_tree)
    
    assert result is not None
```

## Best Practices

### 1. Keep Tasks Focused

Each task should do one thing well:

```python
# Good: Focused task
class FetchUserDataTask(ExecutableTask):
    # Only fetches user data

# Bad: Does too much
class ProcessEverythingTask(ExecutableTask):
    # Fetches, processes, saves, sends notifications, etc.
```

### 2. Validate Inputs

Always validate inputs:

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    url = inputs.get("url")
    if not url:
        raise ValueError("URL is required")
    
    if not isinstance(url, str):
        raise TypeError("URL must be a string")
    
    # Continue with execution
```

### 3. Handle Errors Gracefully

Return meaningful error messages:

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = perform_operation(inputs)
        return {"status": "completed", "result": result}
    except SpecificError as e:
        return {
            "status": "failed",
            "error": f"Operation failed: {str(e)}",
            "error_code": "SPECIFIC_ERROR"
        }
```

### 4. Use Async Properly

Use async/await for I/O operations:

```python
# Good: Async I/O
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
    return {"status": "completed", "data": data}

# Bad: Blocking I/O
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    import requests
    response = requests.get(url)  # Blocking!
    return {"status": "completed", "data": response.json()}
```

### 5. Document Your Tasks

Add clear documentation:

```python
class MyCustomTask(ExecutableTask):
    """
    Custom task that performs specific operations.
    
    This task processes input data and returns processed results.
    It supports various processing modes and configurations.
    """
    
    @property
    def description(self) -> str:
        return "Processes input data using configured processing mode"
```

## Next Steps

- Learn about [Task Orchestration](task-orchestration.md)
- See [API Reference](api-reference.md) for detailed API documentation
- Check [Examples](../examples/basic_task.md) for more examples
- Read [Extending the Framework](../development/extending.md) for advanced topics

