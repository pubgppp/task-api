"""Behavioural tests for validation, CRUD and filtering."""

from fastapi.testclient import TestClient


def create_user(client: TestClient, email: str = "alex@example.com") -> int:
    response = client.post("/users", json={"name": "Alex", "email": email})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_task_and_get_it(client: TestClient) -> None:
    assignee_id = create_user(client)
    response = client.post(
        "/tasks",
        json={
            "title": "  Prepare roster  ",
            "description": "For Monday",
            "assignee_id": assignee_id,
        },
    )
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Prepare roster"
    assert task["status"] == "pending"
    assert task["assignee_id"] == assignee_id
    assert task["created_at"]
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_rejects_invalid_fields(client: TestClient) -> None:
    assert client.post("/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/users", json={"name": "Alex", "email": "bad-email"}).status_code == 422
    created = client.post("/tasks", json={"title": "Valid"}).json()
    assert client.patch(f"/tasks/{created['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/tasks/{created['id']}", json={"status": "unknown"}).status_code == 422


def test_missing_task_and_assignee_return_404(client: TestClient) -> None:
    assert client.get("/tasks/999").status_code == 404
    assert client.patch("/tasks/999", json={"status": "completed"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404
    assert client.post("/tasks", json={"title": "Valid", "assignee_id": 999}).status_code == 404


def test_update_filter_unassign_and_delete(client: TestClient) -> None:
    alex = create_user(client)
    sam = create_user(client, "sam@example.com")
    first = client.post("/tasks", json={"title": "First", "assignee_id": alex}).json()
    client.post("/tasks", json={"title": "Second", "assignee_id": sam})

    response = client.patch(
        f"/tasks/{first['id']}", json={"status": "completed", "assignee_id": sam}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert [task["id"] for task in client.get("/tasks?status=completed").json()] == [first["id"]]
    assert len(client.get(f"/tasks?assignee_id={sam}").json()) == 2
    assert len(client.get("/tasks?status=pending&limit=1&offset=0").json()) == 1

    assert client.patch(f"/tasks/{first['id']}", json={"assignee_id": None}).json()[
        "assignee_id"
    ] is None
    assert client.delete(f"/tasks/{first['id']}").status_code == 204
    assert client.get(f"/tasks/{first['id']}").status_code == 404


def test_duplicate_email_and_unknown_reassignment(client: TestClient) -> None:
    create_user(client)
    assert client.post(
        "/users", json={"name": "Other", "email": "alex@example.com"}
    ).status_code == 409
    task = client.post("/tasks", json={"title": "Keep assignment"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"assignee_id": 999}).status_code == 404
    assert client.get(f"/tasks/{task['id']}").json()["assignee_id"] is None


def test_health_checks_database(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

