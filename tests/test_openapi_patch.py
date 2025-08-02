import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_validation_error_handler import setup_validation_error_handling


class Item(BaseModel):
    name: str
    price: float


def create_test_app():
    app = FastAPI()
    setup_validation_error_handling(app)

    @app.post("/items/")
    async def create_item(item: Item):
        return item

    return app


@pytest.fixture
def client():
    app = create_test_app()
    return TestClient(app)


def test_openapi_schema_status_code(client):
    """Test that the OpenAPI schema shows 400 instead of 422 for validation errors."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    # Check the /items/ path POST operation
    item_post = schema["paths"]["/items/"]["post"]
    responses = item_post["responses"]

    # Ensure 400 is in responses
    assert "400" in responses

    # Ensure 422 is not in responses
    assert "422" not in responses

    # Check the response structure
    error_response = responses["400"]
    assert "content" in error_response
    assert "application/json" in error_response["content"]

    # The schema might contain an example or schema object
    content_json = error_response["content"]["application/json"]

    # If example is present, check it
    if "example" in content_json:
        example = content_json["example"]
        assert "error" in example
        assert "code" in example["error"]
        assert "details" in example["error"]
        assert example["error"]["code"] == "VALIDATION_ERROR"


def test_openapi_schema_content(client):
    """Test that the OpenAPI schema has the correct content structure."""
    response = client.get("/openapi.json")
    schema = response.json()

    # The schema should include components for the models
    assert "components" in schema
    assert "schemas" in schema["components"]
    assert "Item" in schema["components"]["schemas"]

    # The Item schema should have the right properties
    item_schema = schema["components"]["schemas"]["Item"]
    assert "properties" in item_schema
    assert "name" in item_schema["properties"]
    assert "price" in item_schema["properties"]
