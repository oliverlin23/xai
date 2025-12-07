"""X Search - Topic-focused tweet retrieval with community-based expansion."""

from .tool import (
    XSearchTool,
    XSearchConfig,
    XSearchRequest,
    XSearchResponse,
    TweetResult,
    XApiClient,
    XApiError,
)
from .communities import (
    SPHERES,
    Sphere,
    get_sphere,
    get_sphere_names,
    get_all_spheres,
    get_sphere_description,
    get_all_spheres_context,
    get_spheres_for_topic,
)

__all__ = [
    "XSearchTool",
    "XSearchConfig",
    "XSearchRequest",
    "XSearchResponse",
    "TweetResult",
    "XApiClient",
    "XApiError",
    "SPHERES",
    "Sphere",
    "get_sphere",
    "get_sphere_names",
    "get_all_spheres",
    "get_sphere_description",
    "get_all_spheres_context",
    "get_spheres_for_topic",
]


