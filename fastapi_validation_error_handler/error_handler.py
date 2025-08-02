import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Setup logging
logger = logging.getLogger("fastapi_validation_error_handler")


def format_field_path(loc: Tuple[Union[str, int], ...]) -> str:
    """Convert a location tuple to a string field path.

    Handles different validation error sources (body, query, path parameters, etc.)

    Examples:
        ('body', 'user', 'email') -> 'user.email'
        ('body', 'users', 0, 'email') -> 'users[0].email'
        ('query', 'page') -> 'query.page'
        ('path', 'item_id') -> 'path.item_id'
    """
    if not loc:
        return ""

    path: List[str] = []
    skip_first = False

    # Special handling based on first element type
    if loc[0] in ("body", "query", "path", "header", "cookie"):
        # For query/path/header/cookie params, include the parameter type in the path
        # For body, skip it as it's implied
        if loc[0] == "body":
            skip_first = True
        else:
            path.append(str(loc[0]))

    for i, item in enumerate(loc):
        # Skip first element if it's "body"
        if i == 0 and skip_first:
            continue

        # Handle integers (list indices)
        if isinstance(item, int) and path:
            path[-1] = f"{path[-1]}[{item}]"
        elif (
            i > 0 or not skip_first
        ):  # Don't add first item twice if we already processed it
            path.append(str(item))

    return ".".join(path)


def custom_validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, Exception],
    error_code: str = "VALIDATION_ERROR",
):
    """Custom handler for validation errors that returns a 400 response with detailed error information.

    Handles both FastAPI's RequestValidationError and Pydantic's ValidationError.

    Args:
        request: The incoming request
        exc: The validation exception
        error_code: The error code to return in the response (defaults to "VALIDATION_ERROR")

    Returns:
        JSONResponse with 400 status code and structured error details
    """
    try:
        errors = []

        # Handle both FastAPI RequestValidationError and Pydantic ValidationError
        validation_errors = getattr(exc, "errors", lambda: [])()

        if not validation_errors and isinstance(exc, Exception):
            # Fallback for other error types
            errors.append({"field": "request", "message": str(exc)})
            logger.warning(
                f"Unexpected error type handled by validation handler: {type(exc)}"
            )
        else:
            for err in validation_errors:
                try:
                    error_info = {
                        "field": format_field_path(err["loc"]),
                        "message": err["msg"],
                    }

                    # Add type information if available
                    if err.get("type"):
                        error_info["type"] = err["type"]

                    errors.append(error_info)
                except Exception as e:
                    # Fallback for unexpected error format
                    logger.warning(
                        f"Error formatting validation error: {e}. Original error: {err}"
                    )
                    errors.append(
                        {"field": "unknown", "message": str(err.get("msg", str(err)))}
                    )

        return JSONResponse(
            status_code=400,
            content={"error": {"code": error_code, "details": errors}},
        )
    except Exception as e:
        # Last resort fallback
        logger.exception(f"Unexpected error in validation error handler: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": error_code,
                    "details": [
                        {"field": "request", "message": "Invalid request format"}
                    ],
                }
            },
        )
