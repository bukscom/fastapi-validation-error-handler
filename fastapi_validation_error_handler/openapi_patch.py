import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi.openapi.utils import get_openapi

# Setup logging
logger = logging.getLogger("fastapi_validation_error_handler")


def _get_schema(app, original_openapi: Optional[Callable] = None) -> Dict[str, Any]:
    """Get the OpenAPI schema, either from the original function or generate a new one.

    Args:
        app: The FastAPI application instance
        original_openapi: The original openapi function to call (if any)

    Returns:
        OpenAPI schema dictionary
    """
    try:
        if original_openapi:
            return original_openapi()
        else:
            return get_openapi(
                title=app.title,
                version=app.version,
                routes=app.routes,
            )
    except Exception as e:
        logger.exception(f"Error generating OpenAPI schema: {e}")
        # If we can't get the schema, try the default method
        return get_openapi(
            title=app.title or "API",
            version=app.version or "0.1.0",
            routes=app.routes,
        )


def _create_validation_error_example(error_code: str) -> Dict[str, Any]:
    """Create example validation error response for OpenAPI docs.

    Args:
        error_code: The error code to use in the example

    Returns:
        Example validation error response
    """
    return {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": error_code,
                        "details": [
                            {
                                "field": "age",
                                "message": "Age must be greater than 0",
                            },
                            {
                                "field": "email",
                                "message": "Value is not a valid email address",
                                "type": "value_error.email",
                            },
                        ],
                    }
                }
            }
        },
    }


def _create_custom_error_schema() -> Dict[str, Any]:
    """Create a custom error schema to replace the default HTTPValidationError.
    
    Returns:
        Custom error schema definition
    """
    return {
        "title": "ValidationErrorResponse",
        "type": "object",
        "properties": {
            "error": {
                "title": "Error",
                "type": "object",
                "properties": {
                    "code": {
                        "title": "Error Code",
                        "type": "string"
                    },
                    "details": {
                        "title": "Error Details",
                        "type": "array",
                        "items": {
                            "title": "ValidationErrorDetail",
                            "type": "object",
                            "properties": {
                                "field": {
                                    "title": "Field Path",
                                    "type": "string"
                                },
                                "message": {
                                    "title": "Error Message",
                                    "type": "string"
                                },
                                "type": {
                                    "title": "Error Type",
                                    "type": "string"
                                }
                            },
                            "required": ["field", "message"]
                        }
                    }
                },
                "required": ["code", "details"]
            }
        },
        "required": ["error"]
    }


def _update_responses(responses: Dict[str, Any], error_code: str) -> Dict[str, Any]:
    """Update the responses dictionary to replace 422 with 400.

    Args:
        responses: The responses dictionary from OpenAPI schema
        error_code: The error code to use in the example

    Returns:
        Updated responses dictionary
    """
    if "422" in responses:
        # Replace 422 with 400
        responses["400"] = responses.pop("422")

        # Update description
        if "description" in responses["400"]:
            responses["400"]["description"] = "Validation Error"
            
        # Update content to reference our custom schema
        if "content" in responses["400"] and "application/json" in responses["400"]["content"]:
            responses["400"]["content"]["application/json"] = {
                "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"},
                "example": {
                    "error": {
                        "code": error_code,
                        "details": [
                            {
                                "field": "age",
                                "message": "Age must be greater than 0",
                            },
                            {
                                "field": "email",
                                "message": "Value is not a valid email address",
                                "type": "value_error.email",
                            },
                        ],
                    }
                }
            }
    else:
        # Add a 400 response if no 422 was present
        responses["400"] = {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"},
                    "example": {
                        "error": {
                            "code": error_code,
                            "details": [
                                {
                                    "field": "age",
                                    "message": "Age must be greater than 0",
                                },
                                {
                                    "field": "email",
                                    "message": "Value is not a valid email address",
                                    "type": "value_error.email",
                                },
                            ],
                        }
                    }
                }
            }
        }

    return responses


def patch_openapi(
    app,
    original_openapi: Optional[Callable] = None,
    error_code: str = "VALIDATION_ERROR",
):
    """Patch the OpenAPI schema to replace 422 responses with 400 responses.

    Args:
        app: The FastAPI application instance
        original_openapi: The original openapi function to call (if any)
        error_code: Error code to use in example responses

    Returns:
        Modified OpenAPI schema dictionary
    """
    # Return cached schema if available
    if app.openapi_schema:
        return app.openapi_schema

    # Get original schema or generate new one
    openapi_schema = _get_schema(app, original_openapi)

    # Update all paths to use 400 instead of 422
    try:
        # Safety check - make sure we have a paths object
        if "paths" not in openapi_schema or not isinstance(
            openapi_schema["paths"], dict
        ):
            logger.warning(
                "OpenAPI schema does not contain expected 'paths' dictionary"
            )
            return openapi_schema

        # Update all paths
        for path in openapi_schema["paths"].values():
            for method in path.values():
                if not isinstance(method, dict):
                    continue

                responses = method.get("responses", {})
                method["responses"] = _update_responses(responses, error_code)

        # Add custom error schema
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        openapi_schema["components"]["schemas"]["ValidationErrorResponse"] = _create_custom_error_schema()

    except Exception as e:
        logger.exception(f"Error patching OpenAPI schema: {e}")

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema
