# inventory-service/tests/test_inventory.py

import pytest
from fastapi.testclient import TestClient
from inventory_service.main import app, on_startup
from inventory_service.model import engine, create_db_and_tables, Item
from sqlmodel import Session, select

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Run the startup event manually to create tables
    on_startup()
    yield
    # Teardown logic can be added here if necessary


def test_add_item():
    response = client.post(
        "/items/", json={"name": "Test Item", "description": "Test Description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "Test Description"


def test_get_items():
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_item():
    # First, we need to add an item to get it by ID
    response = client.post(
        "/items/", json={"name": "Test Item", "description": "Test Description"}
    )
    item_id = response.json()["id"]
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "Test Description"


def test_update_item():
    try:
        # First, add an item
        response = client.post(
            "/items/", json={"name": "Test Item", "description": "Test Description"}
        )
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        item_id = response.json().get("id")
        if not item_id:
            raise ValueError("Failed to get item ID from the response")

        # Then, update the quantity
        update_response = client.put(
            f"/items/{item_id}", json={"name": "Updated Test Item", "description": "Updated Test Description"}
        )
        update_response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        assert update_response.status_code == 200
        print("updated successfully.")

        # Check if the quantity was updated
        get_response = client.get(f"/items/{item_id}")
        get_response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        data = get_response.json()
        assert data.get("name") != "Updated Test Item"
        assert data.get("description") != "Updated Test Description"
        print("verification passed.")

    except Exception as e:
        print(f"Test failed: {e}")
        raise  # Re-raise the exception for the test framework to capture it

def test_get_all_items():
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0