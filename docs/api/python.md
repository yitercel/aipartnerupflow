# Core API Reference

This document provides a complete reference for aipartnerupflow's core APIs.

## Overview

The core API consists of:
- **TaskManager**: Task orchestration and execution
- **ExecutableTask**: Interface for all task executors
- **TaskTreeNode**: Task tree structure
- **TaskRepository**: Database operations
- **TaskCreator**: Task tree creation from arrays

## TaskManager

The main class for orchestrating and executing task trees.

### Initialization

```python
from aipartnerupflow import TaskManager, create_session

db = create_session()
task_manager = TaskManager(
    db,
    root_task_id=None,              # Optional: Root task ID for streaming
    pre_hooks=None,                 # Optional: List of pre-execution hooks
    post_hooks=None,                # Optional: List of post-execution hooks
    executor_instances=None         # Optional: Shared executor instances dict
)
```

**Parameters**:
- `db` (Session | AsyncSession): Database session
- `root_task_id` (str, optional): Root task ID for streaming callbacks
- `pre_hooks` (List[TaskPreHook], optional): Pre-execution hook functions
- `post_hooks` (List[TaskPostHook], optional): Post-execution hook functions
- `executor_instances` (Dict[str, Any], optional): Shared executor instances for cancellation

### Methods

#### `distribute_task_tree(task_tree, use_callback=True)`

Execute a task tree with proper dependency management and priority scheduling.

```python
result = await task_manager.distribute_task_tree(
    task_tree: TaskTreeNode,
    use_callback: bool = True
) -> TaskTreeNode
```

**Parameters**:
- `task_tree` (TaskTreeNode): Root task tree node
- `use_callback` (bool): Whether to use callbacks (default: True)

**Returns**: TaskTreeNode with execution results

**Example**:
```python
task_tree = TaskTreeNode(root_task)
task_tree.add_child(TaskTreeNode(child_task))
result = await task_manager.distribute_task_tree(task_tree)
```

#### `distribute_task_tree_with_streaming(task_tree, use_callback=True)`

Execute a task tree with real-time streaming for progress updates.

```python
await task_manager.distribute_task_tree_with_streaming(
    task_tree: TaskTreeNode,
    use_callback: bool = True
) -> None
```

**Parameters**:
- `task_tree` (TaskTreeNode): Root task tree node
- `use_callback` (bool): Whether to use callbacks (default: True)

**Note**: Requires streaming callbacks to be configured.

#### `cancel_task(task_id, error_message=None)`

Cancel a running task execution.

```python
result = await task_manager.cancel_task(
    task_id: str,
    error_message: str | None = None
) -> Dict[str, Any]
```

**Parameters**:
- `task_id` (str): Task ID to cancel
- `error_message` (str, optional): Optional error message

**Returns**: Dictionary with cancellation result

**Example**:
```python
result = await task_manager.cancel_task("task_123", "User requested cancellation")
```

### Properties

- `task_repository` (TaskRepository): Access to task repository for database operations
- `streaming_callbacks` (StreamingCallbacks): Streaming callbacks instance

## ExecutableTask

Abstract base class for all task executors.

### Interface

```python
from aipartnerupflow import ExecutableTask
from typing import Dict, Any

class MyTask(ExecutableTask):
    @property
    def id(self) -> str:
        """Unique identifier"""
        return "my_task"
    
    @property
    def name(self) -> str:
        """Display name"""
        return "My Task"
    
    @property
    def description(self) -> str:
        """Description"""
        return "Task description"
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task logic"""
        return {"status": "completed", "result": "..."}
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for inputs"""
        return {
            "type": "object",
            "properties": {...}
        }
    
    async def cancel(self) -> Dict[str, Any]:
        """Optional: Cancel execution"""
        return {"status": "cancelled"}
```

### Required Methods

#### `id` (property)

Unique identifier for the task. Used for registration and references.

#### `name` (property)

Human-readable name for the task.

#### `description` (property)

Description of what the task does.

#### `execute(inputs)`

Main execution logic. Must be async.

**Parameters**:
- `inputs` (Dict[str, Any]): Input parameters

**Returns**: Dict[str, Any] with execution result

#### `get_input_schema()`

Return JSON Schema defining input parameters.

**Returns**: Dict[str, Any] with JSON Schema

### Optional Methods

#### `cancel()`

Cancel task execution (optional). Implement if task supports cancellation.

**Returns**: Dict[str, Any] with cancellation result

## TaskTreeNode

Represents a node in a task tree structure.

### Initialization

```python
from aipartnerupflow.core.types import TaskTreeNode

node = TaskTreeNode(task: TaskModel)
```

**Parameters**:
- `task` (TaskModel): The task model instance

### Methods

#### `add_child(child)`

Add a child node to this node.

```python
node.add_child(child: TaskTreeNode) -> None
```

**Parameters**:
- `child` (TaskTreeNode): Child node to add

**Example**:
```python
root = TaskTreeNode(root_task)
child = TaskTreeNode(child_task)
root.add_child(child)
```

#### `calculate_progress()`

Calculate progress of the task tree.

```python
progress = node.calculate_progress() -> float
```

**Returns**: Average progress (0.0 to 1.0)

#### `calculate_status()`

Calculate overall status of the task tree.

```python
status = node.calculate_status() -> str
```

**Returns**: Status string ("completed", "failed", "in_progress", or "pending")

### Properties

- `task` (TaskModel): The task model instance
- `children` (List[TaskTreeNode]): List of child nodes

## TaskRepository

Database operations for tasks.

### Initialization

```python
from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository

repository = TaskRepository(
    db: Session | AsyncSession,
    task_model_class: Type[TaskModel] = TaskModel
)
```

### Methods

#### `create_task(...)`

Create a new task in the database.

```python
task = await repository.create_task(
    name: str,
    user_id: str,
    parent_id: str | None = None,
    priority: int = 2,
    dependencies: List[Dict[str, Any]] | None = None,
    inputs: Dict[str, Any] | None = None,
    schemas: Dict[str, Any] | None = None,
    status: str = "pending",
    **kwargs
) -> TaskModel
```

**Parameters**:
- `name` (str): Task name (executor identifier)
- `user_id` (str): User ID
- `parent_id` (str, optional): Parent task ID
- `priority` (int): Priority level (default: 2)
- `dependencies` (List[Dict], optional): Task dependencies
- `inputs` (Dict, optional): Input parameters
- `schemas` (Dict, optional): Task schemas
- `status` (str): Initial status (default: "pending")

**Returns**: Created TaskModel instance

#### `get_task_by_id(task_id)`

Get a task by its ID.

```python
task = await repository.get_task_by_id(task_id: str) -> TaskModel | None
```

#### `get_root_task(task)`

Get the root task for a given task.

```python
root = await repository.get_root_task(task: TaskModel) -> TaskModel
```

#### `build_task_tree(task)`

Build a task tree starting from a task.

```python
tree = await repository.build_task_tree(task: TaskModel) -> TaskTreeNode
```

## TaskCreator

Create task trees from task arrays.

### Initialization

```python
from aipartnerupflow.core.execution.task_creator import TaskCreator

creator = TaskCreator(db: Session | AsyncSession)
```

### Methods

#### `create_task_tree_from_array(tasks)`

Create a task tree from an array of task dictionaries.

```python
tree = await creator.create_task_tree_from_array(
    tasks: List[Dict[str, Any]]
) -> TaskTreeNode
```

**Parameters**:
- `tasks` (List[Dict]): Array of task dictionaries

**Task Dictionary Format**:
```python
{
    "id": "task_1",                    # Optional: Task ID
    "name": "Task 1",                  # Required: Task name
    "user_id": "user_123",             # Required: User ID
    "parent_id": "parent_task_id",     # Optional: Parent task ID
    "priority": 1,                     # Optional: Priority (default: 2)
    "dependencies": [                 # Optional: Dependencies
        {"id": "task_0", "required": True}
    ],
    "inputs": {"key": "value"},        # Optional: Input parameters
    "schemas": {...}                   # Optional: Task schemas
}
```

**Returns**: TaskTreeNode root node

**Example**:
```python
tasks = [
    {
        "id": "task_1",
        "name": "task1",
        "user_id": "user123",
        "priority": 1
    },
    {
        "id": "task_2",
        "name": "task2",
        "user_id": "user123",
        "parent_id": "task_1",
        "dependencies": [{"id": "task_1", "required": True}]
    }
]
tree = await creator.create_task_tree_from_array(tasks)
```

## TaskModel

Database model for tasks.

### Fields

- `id` (str): Task ID (primary key)
- `parent_id` (str, optional): Parent task ID
- `user_id` (str, optional): User ID
- `name` (str): Task name
- `status` (str): Task status
- `priority` (int): Priority level
- `dependencies` (JSON): Task dependencies
- `inputs` (JSON): Input parameters
- `params` (JSON): Executor parameters
- `result` (JSON): Execution result
- `error` (str, optional): Error message
- `schemas` (JSON): Task schemas
- `progress` (Decimal): Progress (0.0 to 1.0)
- `has_children` (bool): Whether task has children
- `created_at` (DateTime): Creation timestamp
- `started_at` (DateTime, optional): Start timestamp
- `updated_at` (DateTime): Update timestamp
- `completed_at` (DateTime, optional): Completion timestamp

### Methods

#### `to_dict()`

Convert model to dictionary.

```python
data = task.to_dict() -> Dict[str, Any]
```

## TaskStatus

Task status constants.

### Constants

- `TaskStatus.PENDING = "pending"`
- `TaskStatus.IN_PROGRESS = "in_progress"`
- `TaskStatus.COMPLETED = "completed"`
- `TaskStatus.FAILED = "failed"`
- `TaskStatus.CANCELLED = "cancelled"`

### Methods

#### `is_terminal(status)`

Check if status is terminal.

```python
is_terminal = TaskStatus.is_terminal(status: str) -> bool
```

#### `is_active(status)`

Check if status is active.

```python
is_active = TaskStatus.is_active(status: str) -> bool
```

## Utility Functions

### Session Management

#### `create_session()`

Create a new database session.

```python
from aipartnerupflow import create_session

db = create_session() -> Session
```

#### `get_default_session()`

Get the default database session.

```python
from aipartnerupflow import get_default_session

db = get_default_session() -> Session
```

### Extension Registry

#### Registering Executors

Register an executor with the extension registry.

**Using decorator (recommended):**
```python
from aipartnerupflow import executor_register, BaseTask

@executor_register()
class MyExecutor(BaseTask):
    id = "my_executor"
    # ...
```

The decorator automatically registers the executor when the class is defined. Simply import the class to make it available.

**Note:** For executors that need runtime configuration, you can register instances directly using `get_registry().register(instance)`, but using the decorator is the recommended approach.

#### `register_pre_hook(hook)`

Register a pre-execution hook.

```python
from aipartnerupflow import register_pre_hook

@register_pre_hook
async def my_pre_hook(task: TaskModel):
    # Modify task.inputs if needed
    pass
```

#### `register_post_hook(hook)`

Register a post-execution hook.

```python
from aipartnerupflow import register_post_hook

@register_post_hook
async def my_post_hook(task: TaskModel, inputs: Dict[str, Any], result: Any):
    # Process result
    pass
```

## Type Definitions

### TaskPreHook

Type alias for pre-execution hook functions.

```python
TaskPreHook = Callable[[TaskModel], Union[None, Awaitable[None]]]
```

### TaskPostHook

Type alias for post-execution hook functions.

```python
TaskPostHook = Callable[[TaskModel, Dict[str, Any], Any], Union[None, Awaitable[None]]]
```

## Error Handling

### Common Exceptions

- `ValueError`: Invalid input parameters
- `RuntimeError`: Execution errors
- `KeyError`: Missing required fields

### Error Response Format

Tasks that fail return:

```python
{
    "status": "failed",
    "error": "Error message",
    "error_type": "ExceptionType"
}
```

## Examples

### Basic Usage

```python
from aipartnerupflow import TaskManager, TaskTreeNode, create_session

db = create_session()
task_manager = TaskManager(db)

# Create task
task = await task_manager.task_repository.create_task(
    name="my_task",
    user_id="user123",
    inputs={"key": "value"}
)

# Build tree
tree = TaskTreeNode(task)

# Execute
result = await task_manager.distribute_task_tree(tree)
```

### With Dependencies

```python
# Create tasks
task1 = await task_manager.task_repository.create_task(
    name="task1",
    user_id="user123"
)

task2 = await task_manager.task_repository.create_task(
    name="task2",
    user_id="user123",
    parent_id=task1.id,
    dependencies=[{"id": task1.id, "required": True}]
)

# Build tree
tree = TaskTreeNode(task1)
tree.add_child(TaskTreeNode(task2))

# Execute
await task_manager.distribute_task_tree(tree)
```

## See Also

- [Task Orchestration Guide](../guides/task-orchestration.md)
- [Custom Tasks Guide](../guides/custom-tasks.md)
- [Architecture Documentation](../architecture/overview.md)

