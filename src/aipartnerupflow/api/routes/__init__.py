"""
Protocol-agnostic route handlers for aipartnerupflow API

This module contains route handlers that can be used by any protocol
(A2A, REST, GraphQL, etc.) to provide task management, system operations,
and API documentation.
"""

from aipartnerupflow.api.routes.base import BaseRouteHandler
from aipartnerupflow.api.routes.tasks import TaskRoutes
from aipartnerupflow.api.routes.system import SystemRoutes
from aipartnerupflow.api.routes.docs import DocsRoutes

__all__ = [
    "BaseRouteHandler",
    "TaskRoutes",
    "SystemRoutes",
    "DocsRoutes",
]

