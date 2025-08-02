from .error_handler import custom_validation_exception_handler
from .openapi_patch import patch_openapi
from fastapi.exceptions import RequestValidationError
try:
    from pydantic import ValidationError
    has_pydantic_validation_error = True
except ImportError:
    has_pydantic_validation_error = False


def setup_validation_error_handling(app):
    # Register for FastAPI's RequestValidationError
    app.add_exception_handler(
        RequestValidationError, custom_validation_exception_handler
    )
    
    # Also register for Pydantic's ValidationError if available
    if has_pydantic_validation_error:
        app.add_exception_handler(
            ValidationError, custom_validation_exception_handler
        )
        
    # Patch the OpenAPI schema to show 400 instead of 422
    app.openapi = lambda: patch_openapi(app)
