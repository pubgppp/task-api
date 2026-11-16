"""HTTP endpoints for task and assignee management."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task, TaskStatus, User
from app.schemas import TaskCreate, TaskRead, TaskUpdate, UserCreate, UserRead

app = FastAPI(title="Task API", version="0.1.0")
DbSession = Annotated[Session, Depends(get_db)]


def require_assignee(db: Session, assignee_id: int | None) -> None:
    if assignee_id is not None and db.get(User, assignee_id) is None:
        raise HTTPException(status_code=404, detail="Assignee not found")


def require_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/health")
def health(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession) -> User:
    user = User(name=payload.name, email=str(payload.email).lower())
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    db.refresh(user)
    return user


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession) -> Task:
    require_assignee(db, payload.assignee_id)
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    db: DbSession,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    assignee_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    query = select(Task)
    if task_status is not None:
        query = query.where(Task.status == task_status)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    query = query.order_by(Task.id).limit(limit).offset(offset)
    return list(db.scalars(query))


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession) -> Task:
    return require_task(db, task_id)


@app.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession) -> Task:
    task = require_task(db, task_id)
    changes = payload.model_dump(exclude_unset=True)
    if "assignee_id" in changes:
        require_assignee(db, changes["assignee_id"])
    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession) -> None:
    db.delete(require_task(db, task_id))
    db.commit()

