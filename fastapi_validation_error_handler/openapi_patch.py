from fastapi.openapi.utils import get_openapi


def patch_openapi(app):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    for path in openapi_schema["paths"].values():
        for method in path.values():
            responses = method.get("responses", {})
            if "422" in responses:
                responses["400"] = responses.pop("422")
            else:
                responses["400"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {
                                    "code": "VALIDATION_ERROR",
                                    "details": [
                                        {
                                            "field": "age",
                                            "message": "Age must be integer",
                                        }
                                    ],
                                }
                            }
                        }
                    },
                }
            method["responses"] = responses
    app.openapi_schema = openapi_schema
    return app.openapi_schema
