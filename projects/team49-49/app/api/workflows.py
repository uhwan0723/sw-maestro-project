from fastapi import APIRouter

from app.workflows.registry import get_workflow_registry


router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
def list_workflows() -> dict:
    return get_workflow_registry()
