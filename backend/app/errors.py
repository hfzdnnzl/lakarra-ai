"""Application error hierarchy.

These typed errors let the service layer translate failures into meaningful API
responses (with an ``error_type`` and appropriate HTTP status).
"""

from __future__ import annotations


class LakarraError(Exception):
    """Base class for all handled application errors."""

    #: Stable machine-readable identifier surfaced to API clients.
    error_type: str = "error"
    #: Suggested HTTP status code for this error.
    http_status: int = 500

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class MissingAPIKeyError(LakarraError):
    error_type = "missing_api_key"
    http_status = 503


class LLMTimeoutError(LakarraError):
    error_type = "timeout"
    http_status = 504


class EmptyResponseError(LakarraError):
    error_type = "empty_response"
    http_status = 502


class LLMCallError(LakarraError):
    """Generic upstream LLM failure (network, 5xx, etc.)."""

    error_type = "llm_error"
    http_status = 502


class InvalidJSONError(LakarraError):
    error_type = "invalid_json"
    http_status = 502


class OutputValidationError(LakarraError):
    error_type = "validation_error"
    http_status = 422


class NotFoundError(LakarraError):
    error_type = "not_found"
    http_status = 404


class MissingAccountHandleError(LakarraError):
    error_type = "missing_account_handle"
    http_status = 400


class TikTokFetchError(LakarraError):
    error_type = "tiktok_fetch_error"
    http_status = 502


class MetricsIncompleteError(LakarraError):
    error_type = "metrics_incomplete"
    http_status = 400


class ConflictError(LakarraError):
    error_type = "conflict"
    http_status = 409


_ERROR_CLASSES = [
    MissingAPIKeyError,
    LLMTimeoutError,
    EmptyResponseError,
    LLMCallError,
    InvalidJSONError,
    OutputValidationError,
    NotFoundError,
    MissingAccountHandleError,
    TikTokFetchError,
    MetricsIncompleteError,
    ConflictError,
]

#: Map of ``error_type`` -> suggested HTTP status.
ERROR_STATUS: dict[str, int] = {cls.error_type: cls.http_status for cls in _ERROR_CLASSES}


def status_for(error_type: str | None, default: int = 500) -> int:
    """Return the HTTP status associated with an ``error_type``."""

    return ERROR_STATUS.get(error_type or "", default)
