# FastAPI Validation Error Handler

[![PyPI version](https://img.shields.io/pypi/v/fastapi-validation-error-handler.svg)](https://pypi.org/project/fastapi-validation-error-handler/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-validation-error-handler.svg)](https://pypi.org/project/fastapi-validation-error-handler/)
[![License](https://img.shields.io/github/license/bukscom/fastapi-validation-error-handler.svg)](https://github.com/bukscom/fastapi-validation-error-handler/blob/main/LICENSE)

A custom validation error handler for FastAPI that returns HTTP 400 status codes with structured
JSON responses and updates OpenAPI documentation accordingly.

## Why Use This Package?

By default, FastAPI returns HTTP 422 (Unprocessable Entity) status codes for validation errors.
However, many API designs prefer using HTTP 400 (Bad Request) for all client-side validation errors.

This package provides:

1. **Consistent HTTP 400 responses** for all validation errors
2. **Structured JSON error format** that's easy to parse and handle
3. **Proper nested field paths** that show the exact location of errors
4. **Automatic OpenAPI documentation updates** that reflect the 400 status code
5. **Simple one-line integration** with any FastAPI application

## Installation

```bash
pip install fastapi-validation-error-handler
```

## Basic Usage

```python
from fastapi import FastAPI
from fastapi_validation_error_handler import setup_validation_error_handling
from pydantic import BaseModel

app = FastAPI()

# Add this single line to enable the custom error handler
setup_validation_error_handling(app)


class User(BaseModel):
    email: str
    age: int


@app.post("/users/")
async def create_user(user: User):
    return user
```

## Error Response Format

When validation errors occur, the response will look like this:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {
        "field": "email",
        "message": "value is not a valid email address"
      },
      {
        "field": "age",
        "message": "value is not a valid integer"
      }
    ]
  }
}
```

### Nested Fields

For nested data structures, field paths are formatted as dot-notation with array indices:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "details": [
      {
        "field": "addresses[0].zip_code",
        "message": "string does not match pattern '^\\d{5}$'"
      }
    ]
  }
}
```

## OpenAPI Documentation

The OpenAPI schema is automatically updated to show 400 responses instead of 422 for validation
errors. This ensures that your API documentation accurately reflects your API's behavior.

## Advanced Usage

### Accessing the Original Handler

If you need to access the original handler for customization:

```python
from fastapi_validation_error_handler import custom_validation_exception_handler

# You can now use or extend the handler as needed
```

### Manual OpenAPI Patch

If you need to manually apply the OpenAPI patch:

```python
from fastapi_validation_error_handler import patch_openapi

# Later in your code
modified_schema = patch_openapi(app)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Project Structure

```
fastapi-validation-error-handler/
├── fastapi_validation_error_handler/  # Python package (note: underscores in directory name)
│   ├── __init__.py
│   ├── error_handler.py
│   └── openapi_patch.py
├── examples/                          # Example applications
│   └── main.py
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_error_handler.py
│   └── test_openapi_patch.py
├── pyproject.toml                     # Package configuration
├── LICENSE
└── README.md
```

**Note:** While the PyPI package name is `fastapi-validation-error-handler` (with hyphens), the
importable Python package name is `fastapi_validation_error_handler` (with underscores).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
