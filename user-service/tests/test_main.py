from fastapi.testclient import TestClient
from user_service.main import app, hash_password

client = TestClient(app)

def test_create_user():
    response = client.post("/users/", json={"username": "testuser", "email": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password_hash" in data

def test_hash_password():
    password = "password123"
    hashed = hash_password(password)
    assert hashed == password  # Update this when hash_password is implemented correctly
