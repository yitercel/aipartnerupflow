"""
Main entry point for aipartnerupflow API service

This is the application layer where environment variables can be used
for service deployment configuration.

Supports multiple network protocols:
- A2A Protocol Server (default): Agent-to-Agent communication protocol
- REST API (future): Direct HTTP REST endpoints

Protocol selection via AIPARTNERUPFLOW_API_PROTOCOL environment variable:
- "a2a" (default): A2A Protocol Server
- "rest" (future): REST API server
"""

import os
import sys
import warnings
import uvicorn
import time
from typing import Optional, Any
from aipartnerupflow import __version__
from aipartnerupflow.core.utils.helpers import get_url_with_host_and_port
from aipartnerupflow.core.utils.logger import get_logger

# Suppress specific warnings for cleaner output
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn")

# Add project root to Python path for development
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Initialize logger
logger = get_logger(__name__)
start_time = time.time()
logger.info("Starting aipartnerupflow service")

# Protocol dependency mapping: protocol -> (module_path, extra_name, description)
# This is the single source of truth for protocol configuration
PROTOCOL_DEPENDENCIES = {
    "a2a": (
        "aipartnerupflow.api.a2a.server",
        "a2a",
        "A2A Protocol Server",
    ),
    "mcp": (
        "aipartnerupflow.api.mcp.server",
        "a2a",  # MCP uses a2a dependencies (httpx, fastapi, starlette)
        "MCP (Model Context Protocol) Server",
    ),
    # Future protocols can be added here:
    # "rest": (
    #     "aipartnerupflow.api.rest.server",
    #     "rest",
    #     "REST API Server",
    # ),
    # "rpc": (
    #     "aipartnerupflow.api.rpc.server",
    #     "rpc",
    #     "RPC API Server",
    # ),
}

# Default protocol
DEFAULT_PROTOCOL = "a2a"


def get_supported_protocols() -> list[str]:
    """
    Get list of supported protocol names
    
    Returns:
        List of supported protocol names
    """
    return list(PROTOCOL_DEPENDENCIES.keys())


def get_protocol_dependency_info(protocol: str) -> tuple[str, str, str]:
    """
    Get dependency information for a protocol
    
    Args:
        protocol: Protocol name
    
    Returns:
        Tuple of (module_path, extra_name, description)
    
    Raises:
        ValueError: If protocol is not supported
    """
    if protocol not in PROTOCOL_DEPENDENCIES:
        supported = ", ".join(get_supported_protocols())
        raise ValueError(
            f"Unsupported protocol '{protocol}'. "
            f"Supported protocols: {supported}"
        )
    return PROTOCOL_DEPENDENCIES[protocol]


def get_default_protocol() -> str:
    """
    Get default protocol name
    
    Returns:
        Default protocol name
    """
    return DEFAULT_PROTOCOL


def get_protocol_from_env() -> str:
    """
    Get protocol from environment variable or return default
    
    Returns:
        Protocol name (lowercased)
    """
    protocol = os.getenv("AIPARTNERUPFLOW_API_PROTOCOL", DEFAULT_PROTOCOL)
    return protocol.lower()


def check_protocol_dependency(protocol: str) -> None:
    """
    Check if dependencies for the specified protocol are installed
    
    Args:
        protocol: Protocol name
    
    Raises:
        ValueError: If protocol is not supported
        ImportError: If protocol dependencies are not installed
    """
    module_path, extra_name, description = get_protocol_dependency_info(protocol)
    
    try:
        # Try to import the protocol server module to check if dependencies are installed
        __import__(module_path)
    except ImportError as e:
        error_msg = str(e)
        # Check if it's a dependency-related error
        if extra_name in error_msg.lower() or "No module named" in error_msg:
            raise ImportError(
                f"{description} dependencies are not installed. "
                f"Please install them using: pip install aipartnerupflow[{extra_name}]"
            ) from e
        raise


# Extension configuration: maps extension names to their dependencies and module paths
# This aligns with pyproject.toml optional-dependencies
EXTENSION_CONFIG: dict[str, dict[str, Any]] = {
    "stdio": {
        "dependencies": [],  # Always available (stdlib)
        "module": "aipartnerupflow.extensions.stdio",
        "classes": [
            ("SystemInfoExecutor", "system_info_executor"),
            ("CommandExecutor", "command_executor"),
        ],
        "always_available": True,
    },
    "crewai": {
        "dependencies": ["crewai"],  # From [crewai] extra
        "module": "aipartnerupflow.extensions.crewai",
        "classes": [("CrewManager", "crewai_executor")],
    },
    "http": {
        "dependencies": ["httpx"],  # From [a2a] extra
        "module": "aipartnerupflow.extensions.http",
        "classes": [("RestExecutor", "rest_executor")],
    },
    "ssh": {
        "dependencies": ["asyncssh"],  # From [ssh] extra
        "module": "aipartnerupflow.extensions.ssh",
        "classes": [("SshExecutor", "ssh_executor")],
    },
    "docker": {
        "dependencies": ["docker"],  # From [docker] extra
        "module": "aipartnerupflow.extensions.docker",
        "classes": [("DockerExecutor", "docker_executor")],
    },
    "grpc": {
        "dependencies": ["grpcio"],  # From [grpc] extra
        "module": "aipartnerupflow.extensions.grpc",
        "classes": [("GrpcExecutor", "grpc_executor")],
    },
    "websocket": {
        "dependencies": ["websockets"],  # From [a2a] extra
        "module": "aipartnerupflow.extensions.websocket",
        "classes": [("WebSocketExecutor", "websocket_executor")],
    },
    "apflow": {
        "dependencies": [],  # Core extension, always available
        "module": "aipartnerupflow.extensions.apflow",
        "classes": [("ApFlowApiExecutor", "apflow_api_executor")],
        "always_available": True,
    },
    "mcp": {
        "dependencies": [],  # Uses stdlib, always available
        "module": "aipartnerupflow.extensions.mcp",
        "classes": [("McpExecutor", "mcp_executor")],
        "always_available": True,
    },
}


def _is_package_installed(package_name: str) -> bool:
    """
    Check if a package is installed using importlib.metadata
    
    For standard library packages, this function tries to import them directly.
    For third-party packages, it checks installed distributions.
    
    Args:
        package_name: Package name to check (e.g., "crewai", "httpx", "os")
    
    Returns:
        True if package is installed/available, False otherwise
    """
    # First, try importing directly (works for stdlib and installed packages)
    try:
        __import__(package_name)
        return True
    except ImportError:
        # If direct import fails, check installed distributions
        # This handles cases where package name differs from import name
        pass
    
    # Check installed distributions for third-party packages
    try:
        # Python 3.8+ has importlib.metadata in stdlib
        from importlib.metadata import distributions
    except ImportError:
        # Python 3.7 fallback (shouldn't be needed as we require 3.10+)
        try:
            from importlib_metadata import distributions
        except ImportError:
            return False
    
    # Check all installed distributions
    for dist in distributions():
        # Normalize package name (handle case differences, hyphens vs underscores)
        dist_name = dist.metadata.get("Name", "").lower().replace("-", "_")
        package_normalized = package_name.lower().replace("-", "_")
        
        if dist_name == package_normalized:
            return True
    
    return False


def _get_extension_enablement_from_env() -> dict[str, bool]:
    """
    Parse environment variables to determine which extensions to enable
    
    Supports two formats:
    1. AIPARTNERUPFLOW_EXTENSIONS=stdio,http,crewai (comma-separated list)
    2. AIPARTNERUPFLOW_ENABLE_<EXTENSION>=true/false (individual flags)
    
    Returns:
        Dictionary mapping extension names to enablement status
    """
    result: dict[str, bool] = {}
    
    # Format 1: Comma-separated list
    extensions_env = os.getenv("AIPARTNERUPFLOW_EXTENSIONS", "").strip()
    if extensions_env:
        enabled_extensions = [e.strip().lower() for e in extensions_env.split(",") if e.strip()]
        # If list is provided, only those are enabled
        for ext_name in EXTENSION_CONFIG.keys():
            result[ext_name] = ext_name.lower() in enabled_extensions
        return result
    
    # Format 2: Individual flags (AIPARTNERUPFLOW_ENABLE_<EXTENSION>)
    for ext_name in EXTENSION_CONFIG.keys():
        env_var = f"AIPARTNERUPFLOW_ENABLE_{ext_name.upper()}"
        env_value = os.getenv(env_var, "").strip().lower()
        if env_value:
            result[ext_name] = env_value in ("true", "1", "yes", "on")
        # If not set, will be determined by auto-detection
    
    return result


def _ensure_extension_registered(executor_class: Any, extension_id: str) -> None:
    """
    Ensure an extension is registered in the registry
    
    This function checks if an extension is already registered, and if not,
    manually registers it. This handles the case where modules were imported
    before but the registry was cleared (e.g., in tests).
    
    Args:
        executor_class: Executor class to register
        extension_id: Expected extension ID
    """
    from aipartnerupflow.core.extensions import get_registry
    registry = get_registry()
    
    # If already registered, nothing to do
    if registry.is_registered(extension_id):
        return
    
    # Module was imported but extension not registered (e.g., registry was cleared)
    # Manually register it
    try:
        from aipartnerupflow.core.extensions.decorators import _register_extension
        from aipartnerupflow.core.extensions.types import ExtensionCategory
        _register_extension(executor_class, ExtensionCategory.EXECUTOR, override=True)
        logger.debug(f"Manually registered extension '{extension_id}'")
    except Exception as reg_error:
        logger.warning(f"Failed to manually register {executor_class.__name__}: {reg_error}")


def initialize_extensions(
    include_stdio: Optional[bool] = None,
    include_crewai: Optional[bool] = None,
    include_http: Optional[bool] = None,
    include_ssh: Optional[bool] = None,
    include_docker: Optional[bool] = None,
    include_grpc: Optional[bool] = None,
    include_websocket: Optional[bool] = None,
    include_apflow: Optional[bool] = None,
    include_mcp: Optional[bool] = None,
    auto_init_examples: bool = True,
    load_custom_task_model: bool = True,
) -> None:
    """
    Initialize aipartnerupflow extensions intelligently
    
    This function automatically detects installed optional dependencies and
    only imports extensions that are available. It can be overridden via:
    1. Function parameters (explicit control)
    2. Environment variables (AIPARTNERUPFLOW_EXTENSIONS or AIPARTNERUPFLOW_ENABLE_*)
    3. Auto-detection (default, based on installed packages)
    
    Args:
        include_stdio: Import stdio extensions (default: auto-detect or True)
        include_crewai: Import CrewAI extension (default: auto-detect)
        include_http: Import HTTP extension (default: auto-detect)
        include_ssh: Import SSH extension (default: auto-detect)
        include_docker: Import Docker extension (default: auto-detect)
        include_grpc: Import gRPC extension (default: auto-detect)
        include_websocket: Import WebSocket extension (default: auto-detect)
        include_apflow: Import ApFlow extension (default: auto-detect or True)
        include_mcp: Import MCP extension (default: auto-detect or True)
        auto_init_examples: Auto-initialize examples data if database is empty
        load_custom_task_model: Load custom TaskModel from environment variable
    """
    logger.info("Initializing aipartnerupflow extensions...")
    
    # Get environment variable overrides
    env_overrides = _get_extension_enablement_from_env()
    
    # Determine which extensions to load
    # Priority: function param > env var > auto-detect
    extension_enablement: dict[str, bool] = {}
    function_params = {
        "stdio": include_stdio,
        "crewai": include_crewai,
        "http": include_http,
        "ssh": include_ssh,
        "docker": include_docker,
        "grpc": include_grpc,
        "websocket": include_websocket,
        "apflow": include_apflow,
        "mcp": include_mcp,
    }
    
    for ext_name, ext_config in EXTENSION_CONFIG.items():
        # Priority: function param > env var > auto-detect
        param_value = function_params.get(ext_name)
        
        if param_value is not None:
            # Explicit function parameter
            extension_enablement[ext_name] = param_value
        elif ext_name in env_overrides:
            # Environment variable override
            extension_enablement[ext_name] = env_overrides[ext_name]
        elif ext_config.get("always_available", False):
            # Always available extensions
            extension_enablement[ext_name] = True
        else:
            # Auto-detect: check if dependencies are installed
            dependencies = ext_config.get("dependencies", [])
            if not dependencies:
                # No dependencies, assume available
                extension_enablement[ext_name] = True
            else:
                # Check if all dependencies are installed
                all_installed = all(_is_package_installed(dep) for dep in dependencies)
                extension_enablement[ext_name] = all_installed
    
    # Import and register enabled extensions
    for ext_name, enabled in extension_enablement.items():
        if not enabled:
            logger.debug(f"Skipping {ext_name} extension (not enabled or dependencies not installed)")
            continue
        
        ext_config = EXTENSION_CONFIG[ext_name]
        module_path = ext_config["module"]
        classes = ext_config["classes"]
        
        try:
            # Import the module
            module = __import__(module_path, fromlist=[cls[0] for cls in classes])
            
            # Register each class
            for class_name, extension_id in classes:
                executor_class = getattr(module, class_name)
                _ensure_extension_registered(executor_class, extension_id)
            
            logger.debug(f"Initialized {ext_name} extension")
        except ImportError as e:
            logger.debug(f"{ext_name} extension not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize {ext_name} extension: {e}")
    
    # Load custom TaskModel if specified
    if load_custom_task_model:
        _load_custom_task_model()
    
    # Auto-initialize examples if needed
    if auto_init_examples:
        _auto_init_examples_if_needed()
    
    logger.info("Extension initialization completed")


def _load_custom_task_model():
    """Load custom TaskModel class from environment variable if specified"""
    task_model_class_path = os.getenv("AIPARTNERUPFLOW_TASK_MODEL_CLASS")
    if task_model_class_path:
        try:
            from importlib import import_module
            from aipartnerupflow import set_task_model_class
            module_path, class_name = task_model_class_path.rsplit(".", 1)
            module = import_module(module_path)
            task_model_class = getattr(module, class_name)
            set_task_model_class(task_model_class)
            logger.info(f"Loaded custom TaskModel: {task_model_class_path}")
        except Exception as e:
            logger.warning(f"Failed to load custom TaskModel from {task_model_class_path}: {e}")


def _auto_init_examples_if_needed():
    """Auto-initialize examples data if database is empty and examples are available"""
    try:
        # Check if examples module is available (requires [examples] or [all] extra)
        try:
            from aipartnerupflow.examples.init import init_examples_data_sync
            from aipartnerupflow.core.storage import get_default_session
            from aipartnerupflow.core.storage.sqlalchemy.task_repository import TaskRepository
            from aipartnerupflow.core.config import get_task_model_class
            from sqlalchemy import select, func
        except ImportError:
            # Examples module not available (not installed with [examples] or [all])
            logger.debug("Examples module not available (requires [examples] or [all] extra)")
            return
        
        # Check if database is empty
        try:
            db_session = get_default_session()
            task_repository = TaskRepository(db_session, task_model_class=get_task_model_class())
            
            # Count total tasks in database (use sync query for simplicity)
            if task_repository.is_async:
                # For async sessions, we'll use a simple approach
                import asyncio
                async def check_and_init():
                    stmt = select(func.count()).select_from(task_repository.task_model_class)
                    result = await db_session.execute(stmt)
                    count = result.scalar() or 0
                    
                    if count == 0:
                        logger.info("Database is empty, initializing examples data...")
                        from aipartnerupflow.examples.init import init_examples_data
                        await init_examples_data(force=False)
                        logger.info("Examples data initialized successfully")
                    else:
                        logger.debug(f"Database has {count} tasks, skipping examples initialization")
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Event loop already running, skip auto-init to avoid issues
                        logger.debug("Event loop already running, skipping auto-init")
                        return
                    else:
                        loop.run_until_complete(check_and_init())
                except RuntimeError:
                    asyncio.run(check_and_init())
            else:
                count = db_session.query(task_repository.task_model_class).count()
                
                if count == 0:
                    logger.info("Database is empty, initializing examples data...")
                    try:
                        created_count = init_examples_data_sync(force=False)
                        if created_count > 0:
                            logger.info(f"Examples data initialized successfully: {created_count} tasks created")
                        else:
                            logger.info("Examples data already exists or initialization skipped")
                    except Exception as init_error:
                        logger.error(f"Failed to initialize examples data: {init_error}", exc_info=True)
                else:
                    logger.debug(f"Database has {count} tasks, skipping examples initialization")
        except Exception as e:
            logger.warning(f"Failed to auto-initialize examples data: {e}", exc_info=True)
            # Don't fail startup if examples initialization fails
    except Exception as e:
        logger.warning(f"Examples auto-initialization check failed: {e}", exc_info=True)
        # Don't fail startup if examples are not available


# Auto-discover built-in extensions (optional, extensions register via @executor_register, @storage_register, @hook_register decorators)
# This ensures extensions are available when TaskManager is used
# Note: This is called at module level for backward compatibility when main.py is imported directly
# For programmatic usage, call initialize_extensions() explicitly before create_app_by_protocol()
try:
    initialize_extensions()
except Exception as e:
    # Don't fail module import if extension initialization fails
    logger.warning(f"Failed to auto-initialize extensions at module level: {e}")


def _create_a2a_server(
    jwt_secret_key: Optional[str],
    jwt_algorithm: str,
    base_url: str,
    enable_system_routes: bool,
    enable_docs: bool = True,
):
    """Create A2A Protocol Server"""
    from aipartnerupflow.api.a2a.server import create_a2a_server
    
    # Get TaskModel class from registry for logging
    from aipartnerupflow.core.config import get_task_model_class
    task_model_class = get_task_model_class()
    
    logger.info(
        f"A2A Protocol Server configuration: "
        f"JWT enabled={bool(jwt_secret_key)}, "
        f"System routes={enable_system_routes}, "
        f"Docs={enable_docs}, "
        f"TaskModel={task_model_class.__name__}"
    )
    
    a2a_server_instance = create_a2a_server(
        verify_token_secret_key=jwt_secret_key,
        verify_token_algorithm=jwt_algorithm,
        base_url=base_url,
        enable_system_routes=enable_system_routes,
        enable_docs=enable_docs,
    )
    
    # Note: build() is now optional - CustomA2AStarletteApplication is directly ASGI callable
    # We call it explicitly here for backward compatibility and to get the built app immediately
    return a2a_server_instance.build()


def _create_mcp_server(
    base_url: str,
    enable_system_routes: bool,
    enable_docs: bool = True,
):
    """Create MCP (Model Context Protocol) Server"""
    from fastapi import FastAPI
    from aipartnerupflow.api.mcp.server import McpServer
    
    logger.info(
        f"MCP Server configuration: "
        f"System routes={enable_system_routes}, "
        f"Docs={enable_docs}"
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="aipartnerupflow MCP Server",
        description="Model Context Protocol server for task orchestration",
        version=__version__
    )
    
    # Create MCP server instance
    mcp_server = McpServer()
    
    # Add MCP HTTP routes
    mcp_routes = mcp_server.get_http_routes()
    for route in mcp_routes:
        app.routes.append(route)
    
    # Add system routes if enabled
    if enable_system_routes:
        from starlette.routing import Route
        from aipartnerupflow.api.routes.system import SystemRoutes
        system_routes = SystemRoutes()
        
        async def system_handler(request):
            return await system_routes.handle_system_requests(request)
        
        app.routes.append(
            Route("/system", system_handler, methods=["POST"])
        )
    
    # Add docs if enabled
    if enable_docs:
        from aipartnerupflow.api.docs.swagger_ui import setup_swagger_ui
        setup_swagger_ui(app)
    
    return app


def _create_rest_server():
    """Create REST API Server (future implementation)"""
    # TODO: Implement REST API server when ready
    raise NotImplementedError(
        "REST API server is not yet implemented. "
        "Please use A2A Protocol Server (set AIPARTNERUPFLOW_API_PROTOCOL=a2a or leave unset)."
    )


def create_app_by_protocol(
    protocol: Optional[str] = None,
    auto_initialize_extensions: bool = True,
) -> Any:
    """
    Create application based on protocol type
    
    This is the main function for creating API applications. It should be used
    by both CLI commands and programmatic API usage.
    
    Args:
        protocol: Protocol type. If None, uses environment variable
                  AIPARTNERUPFLOW_API_PROTOCOL or defaults to "a2a"
        auto_initialize_extensions: If True, automatically initialize all extensions
                                   before creating the app (default: True)
    
    Returns:
        Starlette/FastAPI application instance
    
    Raises:
        ValueError: If protocol is not supported
        ImportError: If protocol dependencies are not installed
    """
    # Auto-initialize extensions if requested
    if auto_initialize_extensions:
        initialize_extensions()
    
    # Determine protocol
    if protocol is None:
        protocol = get_protocol_from_env()
    else:
        protocol = protocol.lower()
    
    # Check if protocol is supported and dependencies are installed
    check_protocol_dependency(protocol)
    
    # Get protocol dependency info for logging
    _, _, description = get_protocol_dependency_info(protocol)
    logger.info(f"Creating {description} application")
    # Common configuration
    jwt_secret_key = os.getenv("AIPARTNERUPFLOW_JWT_SECRET_KEY")
    jwt_algorithm = os.getenv("AIPARTNERUPFLOW_JWT_ALGORITHM", "HS256")
    enable_system_routes = os.getenv("AIPARTNERUPFLOW_ENABLE_SYSTEM_ROUTES", "true").lower() in ("true", "1", "yes")
    enable_docs = os.getenv("AIPARTNERUPFLOW_ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
    host = os.getenv("AIPARTNERUPFLOW_API_HOST", os.getenv("API_HOST", "0.0.0.0"))
    port = int(os.getenv("AIPARTNERUPFLOW_API_PORT", os.getenv("PORT", "8000")))
    default_url = get_url_with_host_and_port(host, port)
    base_url = os.getenv("AIPARTNERUPFLOW_BASE_URL", default_url)
    
    # Create app based on protocol
    if protocol == "a2a":
        return _create_a2a_server(
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=jwt_algorithm,
            base_url=base_url,
            enable_system_routes=enable_system_routes,
            enable_docs=enable_docs,
        )
    elif protocol == "mcp":
        return _create_mcp_server(
            base_url=base_url,
            enable_system_routes=enable_system_routes,
            enable_docs=enable_docs,
        )
    elif protocol == "rest":
        return _create_rest_server()
    else:
        raise ValueError(
            f"Unknown protocol: {protocol}. "
            f"Supported protocols: 'a2a', 'mcp', 'rest' (future). "
            f"Set AIPARTNERUPFLOW_API_PROTOCOL environment variable."
        )


def main():
    """
    Main entry point for API service (can be called via entry point)
    
    Protocol selection via AIPARTNERUPFLOW_API_PROTOCOL environment variable:
    - "a2a" (default): A2A Protocol Server
    - "mcp": MCP (Model Context Protocol) Server
    - "rest" (future): REST API server
    """
    # Log startup time
    startup_time = time.time() - start_time
    logger.info(f"Service initialization completed in {startup_time:.2f} seconds")
    
    # Load custom TaskModel if specified
    _load_custom_task_model()
    
    # Auto-initialize examples data if database is empty
    _auto_init_examples_if_needed()
    
    # Determine protocol (default to A2A for backward compatibility)
    protocol = get_protocol_from_env()
    logger.info(f"Starting API service with protocol: {protocol}")
    
    # Create app based on protocol
    app = create_app_by_protocol(protocol)
    
    # Service-level configuration
    host = os.getenv("AIPARTNERUPFLOW_API_HOST", os.getenv("API_HOST", "0.0.0.0"))
    port = int(os.getenv("AIPARTNERUPFLOW_API_PORT", os.getenv("PORT", "8000")))
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,  # Single worker for async app
        loop="asyncio",  # Use asyncio event loop
        limit_concurrency=100,  # Increase concurrency limit
        limit_max_requests=1000,  # Increase max requests
        access_log=True  # Enable access logging for debugging
    )


if __name__ == "__main__":
    main()

