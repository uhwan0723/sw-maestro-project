from fastapi import APIRouter, Depends

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.services.graph import KnowledgeGraphService

router = APIRouter(prefix="/api/workspaces/{workspace_id}/graph", tags=["graph"])


@router.get("")
def get_workspace_graph(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return KnowledgeGraphService(repository).build_workspace_graph(workspace_id)
