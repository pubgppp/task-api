# Task API

A small REST API for teams that need to assign work, see what is still pending, and record completion. It is deliberately narrow in scope so the repository can show the parts needed to run and maintain a backend service: typed contracts, a relational database, migrations, tests, container startup and CI.

## What it does

- Creates users who can own tasks.
- Creates, reads, updates and deletes tasks.
- Assigns or unassigns a task with `assignee_id`.
- Marks a task complete with `PATCH /tasks/{id}` and `{"status":"completed"}`.
- Filters tasks by `status` and `assignee_id`, with bounded pagination.
- Exposes `/health` to check database connectivity and `/docs` for OpenAPI documentation.

The API uses FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic and PostgreSQL. Tests use an isolated SQLite database for fast behavioural checks; CI also applies the migration to PostgreSQL.

## Run locally with Docker

Install Docker with Compose, then run:

```sh
docker compose up --build
```

Compose starts PostgreSQL, waits until it is ready, applies the Alembic migration and starts the API. Open [http://localhost:8000/docs](http://localhost:8000/docs). The example database credentials in `compose.yaml` are for local development; set `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD` in your environment to override them.

Try the API:

```sh
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d '{"name":"Alex","email":"alex@example.com"}'
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Prepare the roster","assignee_id":1}'
curl -X PATCH http://localhost:8000/tasks/1 -H "Content-Type: application/json" -d '{"status":"completed"}'
curl "http://localhost:8000/tasks?status=completed&assignee_id=1"
```

The database is stored in a named Docker volume. `docker compose down` stops the services; `docker compose down -v` also deletes local task data.

## Run tests

Use Python 3.12 or newer:

```sh
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
# After activation:
python -m pip install -e ".[dev]"
pytest -q
ruff check .
```

The test suite covers successful creation and lookup, invalid input, missing records, assignment, completion, filters, deletion and duplicate emails. It does not require a running PostgreSQL server. CI runs the same checks and verifies that the migration applies to PostgreSQL.

## API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/users` | Create an assignee |
| `POST` | `/tasks` | Create a task |
| `GET` | `/tasks` | List and filter tasks |
| `GET` | `/tasks/{id}` | Get one task |
| `PATCH` | `/tasks/{id}` | Edit title, description, status or assignee |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `GET` | `/health` | Check database connectivity |

`GET /tasks` accepts `status=pending|completed`, `assignee_id`, `limit` (1–100, default 50) and `offset` (default 0). Unknown task or assignee IDs return `404`; a duplicate user email returns `409`; invalid request data returns `422`. Set `assignee_id` to `null` to unassign a task. `title` and `status` cannot be set to `null`.

## Design notes

- One SQLAlchemy session is used per request. PostgreSQL is the runtime database, and schema changes are applied by Alembic at startup.
- Task reads are ordered by ID so pagination is deterministic. The database indexes email, assignee and the status/assignee filter.
- The `/health` endpoint runs a database query, so it checks connectivity as well as the HTTP process.
- Authentication, authorization and deployment infrastructure are outside this project's scope. Add them before exposing the API to untrusted users.

