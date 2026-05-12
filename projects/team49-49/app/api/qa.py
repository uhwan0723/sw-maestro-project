from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.workflows.qa import RetrievalQAWorkflow
from fastapi import Request

router = APIRouter(prefix="/api/workspaces/{workspace_id}/qa", tags=["qa"])


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


@router.post("")
def ask_question(
    request: Request,
    workspace_id: int,
    payload: QuestionRequest,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    settings = request.app.state.settings
    return RetrievalQAWorkflow(
        repository,
        upstage_api_key=settings.upstage_api_key,
    ).answer(
        workspace_id=workspace_id,
        question=payload.question,
    )


@router.get("/history")
def list_qa_history(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    return repository.list_chat_history(workspace_id)
