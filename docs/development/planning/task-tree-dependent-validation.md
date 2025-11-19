# Task Tree Dependent Validation and Task Copy Feature

## Overview

This document outlines the plan to enhance task tree construction with dependent validation and implement the task copy feature to support task tree re-execution with dependent task handling.

## Goals

1. **Enhanced Dependency Validation**: Add validation for dependent tasks when constructing task trees
2. **Task Copy Feature**: Implement `create_task_copy` functionality to support task tree re-execution with dependent task handling

## Current State

### Current Implementation

- **TaskCreator** (`core/execution/task_creator.py`):
  - Has `_validate_dependencies()` method that validates dependencies exist in the array
  - Validates dependency references (by id or name)
  - Validates hierarchy (dependency should be at earlier index)
  - **Missing**: Validation of dependent tasks (tasks that depend on the current task)
  - **Missing**: Task copy functionality for re-execution

### Required Features

The following features need to be implemented:

1. **Dependent Task Validation**: When constructing a task tree, validate that all tasks that depend on tasks in the tree are also included
2. **Task Copy Functionality**: Create a copy of a task tree for re-execution that:
   - Creates a copy of task tree for re-execution
   - Automatically includes dependent tasks (tasks that depend on copied tasks)
   - Handles transitive dependencies
   - Special handling for failed leaf nodes
   - Builds minimal subtree containing required tasks

## Feature 1: Dependent Task Validation

### Requirements

When constructing a task tree, validate that:

1. **Dependent Task Detection**: Identify all tasks that depend on each task in the tree
2. **Dependency Completeness**: Ensure all dependent tasks are included in the tree
3. **Circular Dependency Detection**: Detect and prevent circular dependencies
4. **Transitive Dependency Validation**: Validate transitive dependencies (A depends on B, B depends on C → A depends on C)

### Implementation Plan

#### Step 1: Add Dependent Task Detection

**Location**: `core/execution/task_creator.py`

**New Method**: `_find_dependent_tasks()`

```python
def _find_dependent_tasks(
    self,
    task_code: str,
    all_tasks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find all tasks that depend on the specified task code.
    
    Args:
        task_code: Task code to find dependents for
        all_tasks: All tasks in the array
        
    Returns:
        List of tasks that depend on the specified task code
    """
```

**Logic**:
- Iterate through all tasks
- Check if task's dependencies include the specified task_code
- Return list of dependent tasks

#### Step 2: Add Transitive Dependency Detection

**New Method**: `_find_transitive_dependents()`

```python
def _find_transitive_dependents(
    self,
    task_codes: Set[str],
    all_tasks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find all tasks that depend on any of the specified task codes (including transitive).
    
    Args:
        task_codes: Set of task codes to find dependents for
        all_tasks: All tasks in the array
        
    Returns:
        List of tasks that depend on any of the specified task codes (directly or transitively)
    """
```

**Logic**:
- Start with direct dependents
- Recursively find dependents of dependents
- Return all transitive dependents

#### Step 3: Enhance `create_task_tree_from_array()`

**Modification**: Add dependent validation step

```python
async def create_task_tree_from_array(
    self,
    tasks: List[Dict[str, Any]],
    validate_dependents: bool = True  # New parameter
) -> TaskTreeNode:
    """
    Create task tree from array with optional dependent validation.
    
    Args:
        tasks: List of task dictionaries
        validate_dependents: If True, validate that all dependent tasks are included
        
    Returns:
        TaskTreeNode root node
    """
    # ... existing validation ...
    
    if validate_dependents:
        # Collect all task codes in the tree
        task_codes = {task.get("code") or task.get("name") for task in tasks}
        
        # Find all dependent tasks
        all_dependent_tasks = self._find_transitive_dependents(task_codes, tasks)
        
        # Check if all dependent tasks are included
        included_task_codes = {task.get("code") or task.get("name") for task in tasks}
        missing_dependents = [
            dep for dep in all_dependent_tasks
            if (dep.get("code") or dep.get("name")) not in included_task_codes
        ]
        
        if missing_dependents:
            raise ValueError(
                f"Missing dependent tasks: {[t.get('name') for t in missing_dependents]}. "
                f"All tasks that depend on tasks in the tree must be included."
            )
```

#### Step 4: Add Circular Dependency Detection

**New Method**: `_detect_circular_dependencies()`

```python
def _detect_circular_dependencies(
    self,
    tasks: List[Dict[str, Any]]
) -> Optional[List[str]]:
    """
    Detect circular dependencies in task array.
    
    Args:
        tasks: List of task dictionaries
        
    Returns:
        List of task names forming a cycle, or None if no cycle
    """
```

**Logic**:
- Build dependency graph
- Use DFS to detect cycles
- Return cycle path if found

### Validation Rules

1. **Dependent Task Inclusion**: All tasks that depend on any task in the tree must be included
2. **Transitive Dependencies**: Include transitive dependents (A → B → C, if copying A, must include B and C)
3. **Circular Dependencies**: Prevent circular dependencies (A depends on B, B depends on A)
4. **Optional Dependencies**: Handle optional dependencies (if `required: false`, dependent task may be excluded)

## Feature 2: Task Copy Functionality

### Requirements

Implement `create_task_copy` method that:

1. **Task Tree Copying**: Create a copy of a task tree for re-execution
2. **Dependent Task Inclusion**: Automatically include tasks that depend on copied tasks
3. **Transitive Dependency Handling**: Handle transitive dependencies
4. **Failed Leaf Node Handling**: Special handling for failed leaf nodes
5. **Minimal Subtree Construction**: Build minimal subtree containing required tasks
6. **Original Task Linking**: Link copied tasks to original tasks via `original_task_id`

### Implementation Plan

#### Step 1: Add Helper Methods

**Location**: `core/execution/task_creator.py` or new `core/execution/task_copier.py`

**Methods to Add**:

1. `_collect_task_codes_from_tree()`: Collect all task codes from a task tree
2. `_find_dependent_tasks_for_codes()`: Find tasks that depend on specified codes
3. `_find_minimal_subtree()`: Find minimal subtree containing required tasks
4. `_copy_task_tree_recursive()`: Recursively copy task tree structure
5. `_create_task_copy_from_original()`: Create new task instance from original

#### Step 2: Implement Main Method

**New Method**: `create_task_copy()`

```python
async def create_task_copy(
    self,
    original_task: TaskModel,
    include_dependents: bool = True
) -> TaskTreeNode:
    """
    Create a copy of a task tree for re-execution.
    
    Process:
    1. Get root task and all tasks in the tree for dependency lookup
    2. Build original_task's subtree (original_task + all its children)
    3. Collect all task codes from the subtree
    4. Find all tasks that depend on these codes (including transitive dependencies)
    5. Collect all required task IDs (original_task subtree + dependent tasks)
    6. Build minimal subtree containing all required tasks
    7. Copy entire tree structure
    8. Save copied tree to database
    9. Mark all original tasks as having copies
    
    Args:
        original_task: Original task to copy (can be root or any task in tree)
        include_dependents: If True, automatically include dependent tasks
        
    Returns:
        TaskTreeNode with copied task tree, all tasks linked to original via original_task_id
    """
```

#### Step 3: Database Schema Updates

**Required Fields**:

- `original_task_id`: Link to original task (needs to be added to TaskModel)
- `has_copy`: Boolean flag indicating if task has been copied (optional, needs to be added to TaskModel)

**Current TaskModel Schema**:
- TaskModel currently has: `id`, `parent_id`, `user_id`, `name`, `status`, `priority`, `dependencies`, `inputs`, `params`, `result`, `error`, `schemas`, `progress`, `has_children`
- **Missing**: `original_task_id`, `has_copy`

**Migration Required**:
- Add `original_task_id` column to TaskModel (nullable, ForeignKey to TaskModel.id)
- Add `has_copy` column to TaskModel (Boolean, default=False)
- Create database migration script

#### Step 4: Integration with TaskManager

**Location**: `core/execution/task_manager.py`

**New Method**: `copy_task_tree()`

```python
async def copy_task_tree(
    self,
    task_id: str,
    include_dependents: bool = True
) -> TaskTreeNode:
    """
    Copy a task tree for re-execution.
    
    Args:
        task_id: ID of task to copy
        include_dependents: If True, include dependent tasks
        
    Returns:
        TaskTreeNode with copied task tree
    """
    # Get original task
    original_task = await self.task_repository.get_task_by_id(task_id)
    if not original_task:
        raise ValueError(f"Task {task_id} not found")
    
    # Create copy
    task_creator = TaskCreator(self.db)
    return await task_creator.create_task_copy(original_task, include_dependents)
```

### Special Handling

#### Failed Leaf Nodes

When copying tasks that contain failed leaf nodes:
- Only copy dependent tasks that are NOT pending
- Pending tasks haven't executed yet, so no need to re-execute them

**Implementation**:

```python
def _has_failed_leaf_nodes(node: TaskTreeNode) -> bool:
    """Check if tree contains any failed leaf nodes"""
    task_status = node.task.status
    is_leaf = not node.children
    is_failed_leaf = (task_status == "failed" and is_leaf)
    
    if is_failed_leaf:
        return True
    
    # Recursively check children
    for child in node.children:
        if _has_failed_leaf_nodes(child):
            return True
    
    return False
```

#### Minimal Subtree Construction

When dependent tasks are found:
- Build minimal subtree that includes original_task + all dependents
- If no dependents: use original_task subtree directly

## Implementation Steps

### Phase 1: Dependent Validation (Priority: High)

1. ✅ Add `_find_dependent_tasks()` method
2. ✅ Add `_find_transitive_dependents()` method
3. ✅ Add `_detect_circular_dependencies()` method
4. ✅ Enhance `create_task_tree_from_array()` with dependent validation
5. ✅ Add unit tests for dependent validation

### Phase 2: Task Copy Feature (Priority: Medium)

1. ✅ Add helper methods for task copying
2. ✅ Implement `create_task_copy()` method
3. ✅ Add database schema support (if needed)
4. ✅ Integrate with TaskManager
5. ✅ Add unit tests for task copying
6. ✅ Add integration tests

### Phase 3: Documentation and Examples (Priority: Low)

1. ✅ Update API documentation
2. ✅ Add usage examples
3. ✅ Update user guide

## Testing Strategy

### Unit Tests

1. **Dependent Validation Tests**:
   - Test direct dependent detection
   - Test transitive dependent detection
   - Test circular dependency detection
   - Test missing dependent error handling

2. **Task Copy Tests**:
   - Test simple task copy
   - Test task copy with dependents
   - Test task copy with transitive dependents
   - Test failed leaf node handling
   - Test minimal subtree construction

### Integration Tests

1. Test end-to-end task copy workflow
2. Test task copy with database persistence
3. Test task copy with task execution

## Implementation Considerations

### Architecture Alignment

The implementation should align with aipartnerupflow's architecture:

- **TaskRepository**: Use existing TaskRepository interface for database operations
- **TaskTreeNode**: Use existing TaskTreeNode structure for tree representation
- **TaskModel**: Use TaskModel (SQLAlchemy model) for database persistence
- **Async/Await**: All methods should be async to match aipartnerupflow's async pattern

### Design Principles

1. **Consistency**: Follow existing patterns in TaskCreator and TaskManager
2. **Error Handling**: Provide clear error messages for validation failures
3. **Performance**: Optimize for large task trees (consider caching dependency graphs)
4. **Extensibility**: Design for future enhancements (e.g., partial tree copying)

## Open Questions

1. **Async Support**: Should `create_task_copy` be async or sync? (Recommendation: async to match aipartnerupflow pattern)
2. **Error Handling**: How should we handle partial copy failures? (Recommendation: rollback entire copy operation)
3. **Performance**: How to optimize for large task trees? (Consider: dependency graph caching, batch database operations)
4. **Validation Strictness**: Should dependent validation be optional or required by default? (Recommendation: optional with flag, default=True)

## References

- Current validation: `aipartnerupflow/core/execution/task_creator.py::_validate_dependencies()`
- Task tree structure: `aipartnerupflow/core/types.py::TaskTreeNode`
- Task model: `aipartnerupflow/core/storage/sqlalchemy/models.py::TaskModel`
- Task repository: `aipartnerupflow/core/storage/sqlalchemy/task_repository.py`

