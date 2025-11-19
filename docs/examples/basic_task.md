# Basic Task Examples

This document provides practical examples for common use cases with aipartnerupflow.

## Example 1: Simple HTTP API Call Task

Create a task that calls an external HTTP API:

```python
from aipartnerupflow import BaseTask, executor_register
from typing import Dict, Any
import aiohttp

@executor_register()
class APICallTask(BaseTask):
    """Task that calls an external HTTP API"""
    
    id = "api_call_task"
    name = "API Call Task"
    description = "Calls an external HTTP API and returns the response"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call"""
        url = inputs.get("url")
        method = inputs.get("method", "GET")
        data = inputs.get("data")
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url) as response:
                    result = await response.json()
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    result = await response.json()
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status": "completed",
                "status_code": response.status,
                "data": result
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
                    "enum": ["GET", "POST"],
                    "description": "HTTP method",
                    "default": "GET"
                },
                "data": {
                    "type": "object",
                    "description": "Request body for POST requests"
                }
            },
            "required": ["url"]
        }
```

**Usage:**
```python
from aipartnerupflow import TaskManager, TaskTreeNode, create_session
# Import the executor (automatically registered via @executor_register())
from my_module import APICallTask

# Create and execute
db = create_session()
task_manager = TaskManager(db)

task = await task_manager.task_repository.create_task(
    name="api_call_task",
    user_id="user123",
    inputs={
        "url": "https://api.example.com/data",
        "method": "GET"
    }
)

task_tree = TaskTreeNode(task)
result = await task_manager.distribute_task_tree(task_tree)
```

## Example 2: Data Processing Task

Process data with validation:

```python
from aipartnerupflow import BaseTask, executor_register
from typing import Dict, Any

@executor_register()
class DataProcessingTask(BaseTask):
    """Task that processes and validates data"""
    
    id = "data_processing"
    name = "Data Processing Task"
    description = "Processes and validates input data"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process data"""
        data = inputs.get("data", [])
        operation = inputs.get("operation", "sum")
        
        if not isinstance(data, list):
            raise ValueError("Data must be a list")
        
        if operation == "sum":
            result = sum(data)
        elif operation == "average":
            result = sum(data) / len(data) if data else 0
        elif operation == "max":
            result = max(data) if data else None
        elif operation == "min":
            result = min(data) if data else None
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            "operation": operation,
            "input_count": len(data),
            "result": result
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Array of numbers to process"
                },
                "operation": {
                    "type": "string",
                    "enum": ["sum", "average", "max", "min"],
                    "description": "Operation to perform",
                    "default": "sum"
                }
            },
            "required": ["data"]
        }
```

## Example 3: Task with Dependencies

Create a task tree where tasks depend on each other:

```python
import asyncio
from aipartnerupflow import TaskManager, TaskTreeNode, create_session
# Import executors (automatically registered via @executor_register())
from my_module import DataProcessingTask, APICallTask

async def main():
    db = create_session()
    task_manager = TaskManager(db)
    
    # Step 1: Fetch data from API
    fetch_task = await task_manager.task_repository.create_task(
        name="api_call_task",
        user_id="user123",
        priority=1,
        inputs={
            "url": "https://api.example.com/data",
            "method": "GET"
        }
    )
    
    # Step 2: Process the fetched data (depends on step 1)
    process_task = await task_manager.task_repository.create_task(
        name="data_processing",
        user_id="user123",
        parent_id=fetch_task.id,
        dependencies=[{"id": fetch_task.id, "required": True}],
        priority=2,
        inputs={
            "data": [],  # Will be populated from fetch_task result
            "operation": "average"
        }
    )
    
    # Build tree
    root = TaskTreeNode(fetch_task)
    root.add_child(TaskTreeNode(process_task))
    
    # Execute (process_task will wait for fetch_task)
    result = await task_manager.distribute_task_tree(root)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Example 4: Using CrewAI (LLM Tasks)

Execute LLM-based tasks using CrewAI:

```python
# Requires: pip install aipartnerupflow[crewai]
from aipartnerupflow.extensions.crewai import CrewManager
from aipartnerupflow import TaskManager, TaskTreeNode, create_session
from aipartnerupflow.core.extensions import get_registry

# Create a CrewAI executor with configuration
# Note: CrewManager uses @executor_register() decorator, but for configured instances,
# you can register the instance directly (this is a special case for executors that need configuration)
crew = CrewManager(
    id="analysis_crew",
    name="Analysis Crew",
    description="Analyzes data using AI agents",
    agents=[
        {
            "role": "Data Analyst",
            "goal": "Analyze the provided data and extract insights",
            "backstory": "You are an expert data analyst"
        }
    ],
    tasks=[
        {
            "description": "Analyze the input data and provide insights",
            "agent": "Data Analyst"
        }
    ]
)

# Register the configured instance (special case for executors with configuration)
get_registry().register(crew)

# Use it like any other executor
db = create_session()
task_manager = TaskManager(db)

task = await task_manager.task_repository.create_task(
    name="analysis_crew",
    user_id="user123",
    inputs={
        "data": "Sales data: Q1=$100k, Q2=$150k, Q3=$200k"
    }
)

task_tree = TaskTreeNode(task)
result = await task_manager.distribute_task_tree(task_tree)
```

## Example 5: Batch Execution

Execute multiple crews as a batch (atomic operation):

```python
# Requires: pip install aipartnerupflow[crewai]
from aipartnerupflow.extensions.crewai import BatchManager, CrewManager

# Create multiple crews
crew1 = CrewManager(
    id="data_collection",
    agents=[{"role": "Collector", "goal": "Collect data"}],
    tasks=[{"description": "Collect data", "agent": "Collector"}]
)

crew2 = CrewManager(
    id="data_analysis",
    agents=[{"role": "Analyst", "goal": "Analyze data"}],
    tasks=[{"description": "Analyze data", "agent": "Analyst"}]
)

# Create batch manager
batch = BatchManager(
    id="data_pipeline",
    name="Data Pipeline Batch",
    works={
        "data_collection": {
            "agents": [{"role": "Collector", "goal": "Collect data"}],
            "tasks": [{"description": "Collect data", "agent": "Collector"}]
        },
        "data_analysis": {
            "agents": [{"role": "Analyst", "goal": "Analyze data"}],
            "tasks": [{"description": "Analyze data", "agent": "Analyst"}]
        }
    }
)

# Register the configured instance (special case for executors with configuration)
from aipartnerupflow.core.extensions import get_registry
get_registry().register(batch)

# Use via TaskManager (same as other executors)
task = await task_manager.task_repository.create_task(
    name="data_pipeline",
    user_id="user123",
    inputs={...}
)
```

## Example 6: Custom Task with Pre/Post Hooks

Use hooks to modify task behavior:

```python
from aipartnerupflow import (
    register_pre_hook,
    register_post_hook,
    TaskManager,
    create_session
)

# Pre-hook: Modify inputs before execution
@register_pre_hook
async def validate_inputs(task):
    """Validate and transform inputs"""
    if task.inputs and "url" in task.inputs:
        # Ensure URL has protocol
        url = task.inputs["url"]
        if not url.startswith(("http://", "https://")):
            task.inputs["url"] = f"https://{url}"

# Post-hook: Log results after execution
@register_post_hook
async def log_results(task, inputs, result):
    """Log execution results"""
    print(f"Task {task.id} completed:")
    print(f"  Inputs: {inputs}")
    print(f"  Result: {result}")

# Hooks are automatically applied to all tasks
db = create_session()
task_manager = TaskManager(db)
# ... create and execute tasks
```

## Example 7: Error Handling

Handle errors gracefully:

```python
from aipartnerupflow import ExecutableTask
from typing import Dict, Any

class RobustTask(ExecutableTask):
    """Task with error handling"""
    
    id = "robust_task"
    name = "Robust Task"
    description = "Task with comprehensive error handling"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with error handling"""
        try:
            # Your task logic
            data = inputs.get("data")
            if not data:
                raise ValueError("Data is required")
            
            # Process data
            result = self._process(data)
            
            return {
                "status": "completed",
                "result": result
            }
        except ValueError as e:
            # Handle validation errors
            return {
                "status": "failed",
                "error": str(e),
                "error_type": "validation_error"
            }
        except Exception as e:
            # Handle other errors
            return {
                "status": "failed",
                "error": str(e),
                "error_type": "execution_error"
            }
    
    def _process(self, data):
        """Internal processing logic"""
        # Your processing code
        return {"processed": data}
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data to process"
                }
            },
            "required": ["data"]
        }
```

## Example 8: Task with Priority

Control execution order with priorities:

```python
# Priority levels:
# 0 = urgent (highest)
# 1 = high
# 2 = normal (default)
# 3 = low (lowest)

# Lower numbers execute first
urgent_task = await task_manager.task_repository.create_task(
    name="urgent_task",
    user_id="user123",
    priority=0,  # Executes first
    inputs={...}
)

normal_task = await task_manager.task_repository.create_task(
    name="normal_task",
    user_id="user123",
    priority=2,  # Executes after urgent_task
    inputs={...}
)
```

## Example 9: Using Custom TaskModel

Extend TaskModel with custom fields:

```python
from aipartnerupflow.core.storage.sqlalchemy.models import TaskModel
from sqlalchemy import Column, String
from aipartnerupflow import set_task_model_class

class ProjectTaskModel(TaskModel):
    """Custom TaskModel with project_id field"""
    __tablename__ = "apflow_tasks"
    
    project_id = Column(String(255), nullable=True, index=True)

# Set custom model before creating tasks
set_task_model_class(ProjectTaskModel)

# Now tasks can have project_id
task = await task_manager.task_repository.create_task(
    name="my_task",
    user_id="user123",
    project_id="proj-123",  # Custom field
    inputs={...}
)
```

## Example 10: CLI Usage

Execute tasks via CLI:

```bash
# Create tasks.json
cat > tasks.json << EOF
[
  {
    "id": "task1",
    "name": "my_executor",
    "user_id": "user123",
    "schemas": {"method": "my_executor"},
    "inputs": {"key": "value"}
  }
]
EOF

# Execute
aipartnerupflow run flow --tasks-file tasks.json

# Check status
aipartnerupflow tasks status task1

# Watch progress
aipartnerupflow tasks watch --task-id task1
```

## See Also

- [Quick Start Guide](../getting-started/quick-start.md)
- [Python API Reference](../api/python.md)
- [Extending the Framework](../development/extending.md)

