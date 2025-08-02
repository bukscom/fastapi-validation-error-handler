from typing import List, Optional

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, EmailStr

from fastapi_validation_error_handler import setup_validation_error_handling


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


def create_test_app():
    app = FastAPI()
    setup_validation_error_handling(app)

    @app.post("/users/")
    async def create_user(user: User):
        return user

    @app.get("/items/{item_id}")
    async def read_item(item_id: int):
        return {"item_id": item_id}

    return app


@pytest.fixture
def client():
    app = create_test_app()
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
    print("response===>", response.json())
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
            "age": -5,  # Must be > 0
            "name": 123,  # Should be a string
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert len(error["details"]) >= 3  # At least 3 errors should be found
