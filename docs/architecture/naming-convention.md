# Naming Convention: extensions/

## Overview

This document describes the `extensions/` directory in the aipartnerupflow project.

## Directory Purpose

### `extensions/` - Framework Extensions

**Purpose**: Framework-provided, production-ready optional extensions

**Characteristics**:
- ✅ Production-grade implementations
- ✅ Full test coverage
- ✅ Maintained by framework maintainers
- ✅ Can have heavy dependencies
- ✅ Installed via extras: `[crewai]`, `[stdio]`
- ✅ Direct use in production
- ✅ Registered through `ExtensionRegistry` system

**Examples**:
- `extensions/crewai/` - CrewAI executor (LLM tasks)
- `extensions/stdio/` - Stdio executor (local command execution)
- `extensions/core/` - Core executors (aggregate_results_executor)
- `extensions/hooks/` - Hook implementations
- `extensions/storage/` - Storage implementations
- `extensions/tools/` - Tool implementations

**Location**: `src/aipartnerupflow/extensions/`

## Learning Resources

For examples and learning templates, see the test cases:
- `tests/integration/` - Integration tests demonstrating real-world usage patterns
- `tests/extensions/` - Extension-specific test examples

Test cases serve as comprehensive examples showing how to:
- Use executors in real scenarios
- Create custom task implementations
- Build task trees with dependencies
- Aggregate results from multiple tasks

## Extension System

All extensions in `extensions/` must:
1. Implement `ExecutableTask` interface (or extend `BaseTask`)
2. Use `@extension_register()` decorator for auto-registration
3. Be registered in `ExtensionRegistry` by unique ID
4. Follow the unified extension system architecture

See [extension-registry-design.md](extension-registry-design.md) for details.

## Summary

- **`extensions/`**: Framework-provided, production-ready executors (CrewAI, Stdio, etc.)
- **Test cases**: Serve as learning resources and examples (see `tests/integration/` and `tests/extensions/`)

Use `extensions/` for production-ready, reusable components. For learning and examples, refer to the test cases.
