# Examples

This page contains examples and use cases for aipartnerupflow.

## Basic Examples

Examples are available in the test cases:

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

For more examples, see the test cases in the main repository.

