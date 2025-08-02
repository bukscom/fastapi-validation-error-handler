import logging
import sys
import warnings
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Union

import fastapi
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .error_handler import custom_validation_exception_handler
from .openapi_patch import patch_openapi

# Setup logging
logger = logging.getLogger("fastapi_validation_error_handler")

# Check FastAPI version
fastapi_version = tuple(int(x) for x in fastapi.__version__.split(".")[:2])

try:
    from pydantic import ValidationError

    has_pydantic_validation_error = True
except ImportError:
    has_pydantic_validation_error = False


def pydantic_handler_wrapper(handler: Callable, request: Any, exc: Exception):
    """Wrapper to adapt Pydantic ValidationError to FastAPI's handler signature."""
    try:
        # Convert Pydantic ValidationError to a format similar to FastAPI's
        # This helps the handler process it correctly
        return handler(request, exc)
    except Exception as e:
        logger.exception(f"Error in pydantic handler wrapper: {e}")
        # Fallback to basic handler if conversion fails
        return handler(request, e)


def setup_validation_error_handling(
    app: FastAPI,
    error_code: str = "VALIDATION_ERROR",
    include_pydantic_errors: bool = True,
):
    """Setup validation error handling on a FastAPI app.

    This function does two things:
    1. Adds an exception handler for validation errors that returns a 400 status code
    2. Patches the OpenAPI schema to show 400 responses instead of 422 for validation errors

    Args:
        app: The FastAPI application instance
        error_code: The error code string to use in responses (default: "VALIDATION_ERROR")
        include_pydantic_errors: Whether to handle Pydantic ValidationError exceptions (default: True)
    """
    # Version compatibility check
    if fastapi_version < (0, 68):
        warnings.warn(
            "This package is tested with FastAPI >= 0.68.0. "
            f"You're using {fastapi.__version__}, which may not be fully compatible.",
            UserWarning,
        )

    # Create handler with configured error code
    handler = partial(custom_validation_exception_handler, error_code=error_code)

    # Add exception handler for FastAPI's RequestValidationError
    app.add_exception_handler(RequestValidationError, handler)

    # Also register for Pydantic's ValidationError if available and requested
    if has_pydantic_validation_error and include_pydantic_errors:
        pydantic_wrapped_handler = partial(pydantic_handler_wrapper, handler)
        app.add_exception_handler(ValidationError, pydantic_wrapped_handler)
        logger.debug("Registered handler for Pydantic ValidationError")

    # Patch the OpenAPI schema to show 400 instead of 422
    original_openapi = app.openapi

    # Define a wrapper function to avoid lint issues with lambda arguments
    def patched_openapi():
        return patch_openapi(app, original_openapi, error_code)

    app.openapi = patched_openapi

    logger.debug(
        f"Validation error handling setup complete with error code: {error_code}"
    )
