from behave import given, when, then
from fastapi.testclient import TestClient
from user_service.main import app

client = TestClient(app)

@given('the user does not exist')
def step_impl(context):
    pass  # Assume database is empty for simplicity

@when('I send a POST request to "/users/" with the user data')
def step_impl(context):
    context.response = client.post("/users/", json={"username": "testuser", "email": "test@example.com", "password": "password123"})

@then('the response status should be 200')
def step_impl(context):
    assert context.response.status_code == 200

@then('the response should contain the user data')
def step_impl(context):
    data = context.response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password_hash" in data
