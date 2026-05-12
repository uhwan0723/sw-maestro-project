from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.services.llm import build_llm_client
from app.workflows.quality_review import QualityReviewWorkflow

router = APIRouter(prefix="/api/workspaces/{workspace_id}", tags=["reviews"])


@router.post("/reviews/run")
def run_quality_review(
    workspace_id: int,
    request: Request,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    llm_client = build_llm_client(request.app.state.settings)
    workflow = QualityReviewWorkflow(repository, llm_client=llm_client)
    return workflow.run(workspace_id)
