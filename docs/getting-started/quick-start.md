# Quick Start Guide

Get started with aipartnerupflow in 5 minutes.

## Installation

### Minimal Installation (Core Only)

```bash
pip install aipartnerupflow
```

This installs the core orchestration framework with no optional dependencies.

### Full Installation (All Features)

```bash
pip install aipartnerupflow[all]
```

This includes:
- Core orchestration framework
- CrewAI support for LLM tasks
- A2A Protocol Server
- CLI tools
- PostgreSQL storage support

## Your First Task

### Step 1: Create a Simple Executor

Create a file `my_executor.py`:

```python
from aipartnerupflow import BaseTask, executor_register
from typing import Dict, Any

@executor_register()
class MyFirstTask(BaseTask):
    """A simple task that processes data"""
    
    id = "my_first_task"
    name = "My First Task"
    description = "Processes input data and returns a result"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task"""
        # Your task logic here
        result = {
            "processed": True,
            "input_received": inputs.get("data", ""),
            "output": f"Processed: {inputs.get('data', 'no data')}"
        }
        return result
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define input parameters"""
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Input data to process"
                }
            },
            "required": ["data"]
        }
```

### Step 2: Register the Executor

Create a file `main.py`:

```python
import asyncio
from aipartnerupflow import (
    TaskManager, 
    TaskTreeNode, 
    create_session
)
# Import the executor (it's automatically registered via @executor_register())
from my_executor import MyFirstTask

async def main():
    # Create database session
    db = create_session()
    
    # Create task manager
    task_manager = TaskManager(db)
    
    # Create a task
    root_task = await task_manager.task_repository.create_task(
        name="my_first_task",  # Must match executor ID
        user_id="user123",
        priority=2,
        inputs={"data": "Hello, aipartnerupflow!"}
    )
    
    # Build task tree
    task_tree = TaskTreeNode(root_task)
    
    # Execute
    result = await task_manager.distribute_task_tree(task_tree)
    
    print(f"Task completed: {result}")
    
    # Get the result
    task = await task_manager.task_repository.get_task_by_id(root_task.id)
    print(f"Task result: {task.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Run It

```bash
python main.py
```

**Output:**
```
Task completed: {...}
Task result: {'processed': True, 'input_received': 'Hello, aipartnerupflow!', 'output': 'Processed: Hello, aipartnerupflow!'}
```

## Using the CLI

### Install CLI Support

```bash
pip install aipartnerupflow[cli]
```

### Execute a Task via CLI

```bash
# Create tasks.json
cat > tasks.json << EOF
[
  {
    "id": "task1",
    "name": "my_first_task",
    "user_id": "user123",
    "schemas": {"method": "my_first_task"},
    "inputs": {"data": "Hello from CLI!"}
  }
]
EOF

# Execute
aipartnerupflow run flow --tasks-file tasks.json
```

## Using the API Server

### Start the Server

```bash
# Install API support
pip install aipartnerupflow[a2a]

# Start server
aipartnerupflow serve start --port 8000
```

### Execute Task via API

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks.create",
    "params": [
      {
        "id": "task1",
        "name": "my_first_task",
        "user_id": "user123",
        "schemas": {"method": "my_first_task"},
        "inputs": {"data": "Hello from API!"}
      }
    ],
    "id": "1"
  }'
```

## Task Tree Example

Create a task tree with dependencies:

```python
import asyncio
from aipartnerupflow import TaskManager, TaskTreeNode, create_session

async def main():
    db = create_session()
    task_manager = TaskManager(db)
    
    # Create root task
    root_task = await task_manager.task_repository.create_task(
        name="root_task",
        user_id="user123",
        priority=1
    )
    
    # Create child tasks
    child1 = await task_manager.task_repository.create_task(
        name="child_task_1",
        user_id="user123",
        parent_id=root_task.id,
        priority=2,
        inputs={"step": 1}
    )
    
    child2 = await task_manager.task_repository.create_task(
        name="child_task_2",
        user_id="user123",
        parent_id=root_task.id,
        dependencies=[{"id": child1.id, "required": True}],
        priority=2,
        inputs={"step": 2}
    )
    
    # Build task tree
    task_tree = TaskTreeNode(root_task)
    task_tree.add_child(TaskTreeNode(child1))
    task_tree.add_child(TaskTreeNode(child2))
    
    # Execute (child2 will wait for child1 to complete)
    result = await task_manager.distribute_task_tree(task_tree)
    print(f"Execution result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- **Learn More**: Read the [Architecture Guide](../architecture/overview.md)
- **API Reference**: See [Python API Reference](../api/python.md) or [HTTP API Reference](../api/http.md)
- **Examples**: Check [Examples](../examples/basic_task.md)
- **Extending**: Learn how to [Extend the Framework](../development/extending.md)

## Common Patterns

### Pattern 1: Simple Task Execution

```python
# Single task, no dependencies
task = await task_manager.task_repository.create_task(
    name="executor_id",
    user_id="user123",
    inputs={"key": "value"}
)
task_tree = TaskTreeNode(task)
result = await task_manager.distribute_task_tree(task_tree)
```

### Pattern 2: Sequential Tasks

```python
# Tasks execute in order based on dependencies
root = await task_manager.task_repository.create_task(...)
task1 = await task_manager.task_repository.create_task(
    parent_id=root.id,
    ...
)
task2 = await task_manager.task_repository.create_task(
    parent_id=root.id,
    dependencies=[{"id": task1.id, "required": True}],
    ...
)
```

### Pattern 3: Parallel Tasks

```python
# Tasks without dependencies execute in parallel
root = await task_manager.task_repository.create_task(...)
task1 = await task_manager.task_repository.create_task(
    parent_id=root.id,
    ...
)
task2 = await task_manager.task_repository.create_task(
    parent_id=root.id,
    # No dependency on task1, so runs in parallel
    ...
)
```

## Troubleshooting

### Task Not Found

**Error:** `Task executor not found: executor_id`

**Solution:** Make sure you've registered the executor using the decorator:
```python
from aipartnerupflow import BaseTask, executor_register

@executor_register()
class MyExecutor(BaseTask):
    id = "my_executor"
    # ...
```

### Database Error

**Error:** Database connection issues

**Solution:** For DuckDB (default), no setup needed. For PostgreSQL:
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost/dbname"
```

### Import Error

**Error:** `ModuleNotFoundError: No module named 'aipartnerupflow'`

**Solution:** Make sure you've installed the package:
```bash
pip install aipartnerupflow
```

## Getting Help

- **Documentation**: [Full Documentation Index](../README.md)
- **Issues**: [GitHub Issues](https://github.com/aipartnerup/aipartnerupflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aipartnerup/aipartnerupflow/discussions)

