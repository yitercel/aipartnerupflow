# Examples

This page contains examples and use cases for aipartnerupflow.

## Demo Task Initialization

> **Note:** The built-in examples module has been removed from aipartnerupflow core library.
> For demo task initialization, please use the **aipartnerupflow-demo** project instead.

The **aipartnerupflow-demo** project provides:
- Complete demo tasks for all executors
- Per-user demo task initialization
- Demo task validation against executor schemas

For more information, see the [aipartnerupflow-demo](https://github.com/aipartnerup/aipartnerupflow-demo) repository.

## Executor Metadata API

aipartnerupflow provides utilities to query executor metadata for demo task generation:

```python
from aipartnerupflow.core.extensions import (
    get_executor_metadata,
    validate_task_format,
    get_all_executor_metadata
)

# Get metadata for a specific executor
metadata = get_executor_metadata("system_info_executor")
# Returns: id, name, description, input_schema, examples, tags

# Validate a task against executor schema
task = {
    "name": "CPU Analysis",
    "schemas": {"method": "system_info_executor"},
    "inputs": {"resource": "cpu"}
}
is_valid = validate_task_format(task, "system_info_executor")

# Get metadata for all executors
all_metadata = get_all_executor_metadata()
```

## Basic Examples

Examples are also available in the test cases:

- Integration tests: `tests/integration/`
- Extension tests: `tests/extensions/`

## Example: Custom Task

```python
from aipartnerupflow import ExecutableTask
from typing import Dict, Any

class MyCustomTask(ExecutableTask):
    id = "my_custom_task"
    name = "My Custom Task"
    description = "A custom task example"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Your task logic here
        return {"result": "success"}
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_field": {"type": "string"}
            }
        }
```

## Example: Task Tree

```python
from aipartnerupflow import TaskManager, TaskTreeNode, create_session

db = create_session()
task_manager = TaskManager(db)

# Create tasks
root = await task_manager.task_repository.create_task(
    name="root",
    user_id="user_123"
)

child1 = await task_manager.task_repository.create_task(
    name="child1",
    user_id="user_123",
    parent_id=root.id
)

child2 = await task_manager.task_repository.create_task(
    name="child2",
    user_id="user_123",
    parent_id=root.id,
    dependencies=[child1.id]  # child2 depends on child1
)

# Build and execute
tree = TaskTreeNode(root)
tree.add_child(TaskTreeNode(child1))
tree.add_child(TaskTreeNode(child2))

result = await task_manager.distribute_task_tree(tree)
```

## Example: CrewAI Task with LLM Key

```python
# Via API with header
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/tasks",
        headers={
            "Content-Type": "application/json",
            "X-LLM-API-KEY": "openai:sk-your-key"  # Provider-specific format
        },
        json={
            "jsonrpc": "2.0",
            "method": "tasks.create",
            "params": {
                "tasks": [{
                    "id": "crewai-task",
                    "name": "CrewAI Research Task",
                    "user_id": "user123",
                    "schemas": {"method": "crewai_executor"},
                    "params": {
                        "works": {
                            "agents": {
                                "researcher": {
                                    "role": "Research Analyst",
                                    "goal": "Research and analyze the given topic",
                                    "llm": "openai/gpt-4"
                                }
                            },
                            "tasks": {
                                "research": {
                                    "description": "Research the topic: {topic}",
                                    "agent": "researcher"
                                }
                            }
                        }
                    },
                    "inputs": {
                        "topic": "Artificial Intelligence"
                    }
                }]
            }
        }
    )
```

For more examples, see the test cases in the main repository.

