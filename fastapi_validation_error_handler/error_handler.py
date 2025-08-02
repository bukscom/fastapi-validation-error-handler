from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import List, Dict, Any, Union


def format_field_path(loc: tuple) -> str:
    """Convert a location tuple to a string field path.

    Examples:
        ('body', 'user', 'email') -> 'user.email'
        ('body', 'users', 0, 'email') -> 'users[0].email'
    """
    path = []
    for item in loc:
        # Skip 'body' which is usually the first element in validation errors
        if item == "body" and not path:
            continue
        # Handle integers (list indices)
        if isinstance(item, int):
            path[-1] = f"{path[-1]}[{item}]"
        else:
            path.append(str(item))

    return ".".join(path)


def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom handler for validation errors that returns a 400 response with detailed error information.

    Args:
        request: The incoming request
        exc: The validation exception

    Returns:
        JSONResponse with 400 status code and structured error details
    """
    errors = []

    for err in exc.errors():
        error_info = {"field": format_field_path(err["loc"]), "message": err["msg"]}

        # Add type information if available
        if err.get("type"):
            error_info["type"] = err["type"]

        errors.append(error_info)

    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "details": errors}},
    )
