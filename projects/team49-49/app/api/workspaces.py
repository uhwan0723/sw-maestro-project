from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return repository.create_workspace(payload.name, payload.description)


@router.get("")
def list_workspaces(repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    return repository.list_workspaces()


@router.get("/{workspace_id}")
def get_workspace(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return repository.get_workspace(workspace_id)
