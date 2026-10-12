"""Authentication and authorization API tests."""

from fastapi.testclient import TestClient

from app.models.user import User


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "securepassword",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["role"] == "customer"
    assert data["user"]["name"] == "John Doe"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_register_duplicate_email(client: TestClient, customer_user: User) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Someone Else",
            "email": customer_user.email,
            "password": "securepassword",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "An account with this email already exists."


def test_login_success(client: TestClient, customer_user: User) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": customer_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == customer_user.email
    assert data["user"]["role"] == "customer"


def test_login_invalid_password(client: TestClient, customer_user: User) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": customer_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_authenticated(client: TestClient, customer_user: User, customer_headers: dict) -> None:
    response = client.get("/api/auth/me", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer_user.id
    assert data["email"] == customer_user.email
    assert data["role"] == "customer"


def test_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_customer_denied_admin_route(client: TestClient, customer_headers: dict) -> None:
    response = client.get("/api/admin/ping", headers=customer_headers)
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to access this resource."
    )


def test_admin_allowed_admin_route(client: TestClient, admin_headers: dict) -> None:
    response = client.get("/api/admin/ping", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["role"] == "admin"


def test_admin_lists_customers(
    client: TestClient,
    admin_headers: dict,
    customer_user: User,
) -> None:
    response = client.get("/api/admin/users?role=customer", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["email"] == customer_user.email
    assert users[0]["role"] == "customer"
    assert "created_at" in users[0]


def test_customer_denied_list_users(client: TestClient, customer_headers: dict) -> None:
    response = client.get("/api/admin/users", headers=customer_headers)
    assert response.status_code == 403


def test_customer_denied_dashboard_route(client: TestClient, customer_headers: dict) -> None:
    response = client.get("/api/dashboard/ping", headers=customer_headers)
    assert response.status_code == 403


def test_logout(client: TestClient, customer_headers: dict) -> None:
    response = client.post("/api/auth/logout", headers=customer_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out."


def test_update_profile_success(
    client: TestClient,
    customer_user: User,
    customer_headers: dict,
) -> None:
    response = client.patch(
        "/api/auth/me",
        headers=customer_headers,
        json={"name": "Jane Doe", "email": "jane@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer_user.id
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane@example.com"


def test_update_profile_duplicate_email(
    client: TestClient,
    customer_headers: dict,
    admin_user: User,
) -> None:
    response = client.patch(
        "/api/auth/me",
        headers=customer_headers,
        json={"name": "Someone", "email": admin_user.email},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "An account with this email already exists."


def test_change_password_success(
    client: TestClient,
    customer_user: User,
    customer_headers: dict,
) -> None:
    response = client.post(
        "/api/auth/change-password",
        headers=customer_headers,
        json={
            "current_password": "password123",
            "new_password": "newsecurepass",
        },
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Password updated successfully."

    login = client.post(
        "/api/auth/login",
        json={"email": customer_user.email, "password": "newsecurepass"},
    )
    assert login.status_code == 200


def test_change_password_wrong_current(
    client: TestClient,
    customer_headers: dict,
) -> None:
    response = client.post(
        "/api/auth/change-password",
        headers=customer_headers,
        json={
            "current_password": "wrong-password",
            "new_password": "newsecurepass",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect."
