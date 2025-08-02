from typing import List, Optional

from fastapi import Depends, FastAPI, Header, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, Field, ValidationError

from fastapi_validation_error_handler import setup_validation_error_handling
import pytest


class Address(BaseModel):
    street: str
    city: str
    zip_code: str = Field(..., pattern=r"^\d{5}$")


class User(BaseModel):
    email: EmailStr
    age: int = Field(..., gt=0)
    name: str
    addresses: List[Address] = []
    tags: Optional[List[str]] = None


def create_test_app(error_code="VALIDATION_ERROR"):
    app = FastAPI()
    setup_validation_error_handling(app, error_code=error_code)

    @app.post("/users/")
    async def create_user(user: User):
        return user

    @app.get("/items/{item_id}")
    async def read_item(item_id: int):
        return {"item_id": item_id}

    @app.get("/search/")
    async def search(q: str = Query(..., min_length=3), page: int = Query(1, gt=0)):
        return {"q": q, "page": page}

    @app.post("/headers-test/")
    async def headers_test(custom_header: str = Header(...)):
        return {"custom_header": custom_header}

    return app


@pytest.fixture
def client():
    app = create_test_app()
    return TestClient(app)


@pytest.fixture
def custom_error_client():
    app = create_test_app(error_code="CUSTOM_VALIDATION_ERROR")
    return TestClient(app)


def test_valid_data(client):
    """Test that valid data passes validation."""
    response = client.post(
        "/users/", json={"email": "test@example.com", "age": 30, "name": "Test User"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["age"] == 30


def test_invalid_data_simple_field(client):
    """Test validation error on a simple field."""
    response = client.post(
        "/users/", json={"email": "not-an-email", "age": 30, "name": "Test User"}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any(e["field"] == "email" for e in error["details"])


def test_invalid_data_nested_field(client):
    """Test validation error on a nested field."""
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "age": 30,
            "name": "Test User",
            "addresses": [
                {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "zip_code": "123",
                }  # Invalid zip
            ],
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"

    # Check that the field path is correctly formatted
    details = error["details"]
    assert any(e["field"] == "addresses[0].zip_code" for e in details)


def test_invalid_data_array_item(client):
    """Test validation error on an array item."""
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "age": 30,
            "name": "Test User",
            "tags": [123],  # Should be strings
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any("tags[0]" in e["field"] for e in error["details"])


def test_invalid_path_parameter(client):
    """Test validation error on a path parameter."""
    response = client.get("/items/not-a-number")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    # The field should contain item_id or path
    assert any(
        "item_id" in e["field"] or "path" in e["field"] for e in error["details"]
    )


def test_multiple_validation_errors(client):
    """Test multiple validation errors in one request."""
    response = client.post(
        "/users/",
        json={
            "email": "not-an-email",
            "age": 0,
            "name": "Test User",
            "addresses": [
                {"street": "123 Main St", "city": "Anytown", "zip_code": "123"}
            ],
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    details = error["details"]
    assert len(details) >= 3  # At least 3 validation errors


def test_invalid_query_parameter(client):
    """Test validation error on query parameters."""
    # Test too short query parameter
    response = client.get("/search/?q=ab&page=1")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    details = error["details"]
    assert any("query.q" in e["field"] for e in details)

    # Test invalid page number
    response = client.get("/search/?q=test&page=0")
    assert response.status_code == 400
    error = response.json()["error"]
    details = error["details"]
    assert any("query.page" in e["field"] for e in details)


def test_missing_header(client):
    """Test validation error on missing header."""
    response = client.post("/headers-test/")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    details = error["details"]
    assert any("header.header.custom-header" in e["field"] for e in details)


def test_custom_error_code(custom_error_client):
    """Test custom error code in validation errors."""
    response = custom_error_client.post(
        "/users/", json={"email": "not-an-email", "age": 30, "name": "Test User"}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "CUSTOM_VALIDATION_ERROR"


def test_direct_pydantic_validation():
    """Test direct Pydantic validation error handling."""
    from fastapi.testclient import TestClient

    app = FastAPI()
    setup_validation_error_handling(app)

    @app.post("/validate/")
    async def validate_data(data: dict):
        try:
            # Manually validate with Pydantic
            user = User(**data)
            return user.model_dump()
        except ValidationError as e:
            # This should be caught by our handler
            raise e

    client = TestClient(app)

    response = client.post(
        "/validate/", json={"email": "not-an-email", "age": 30, "name": "Test User"}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
