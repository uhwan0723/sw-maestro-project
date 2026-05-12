from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.services.paths import MultiHopPathService

router = APIRouter(prefix="/api/workspaces/{workspace_id}/cards", tags=["cards"])


class CardUpdate(BaseModel):
    status: str | None = None
    tags: list[str] | None = None


@router.get("")
def list_cards(
    workspace_id: int,
    card_type: str | None = None,
    status: str | None = None,
    confidence: str | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    repository: SQLiteRepository = Depends(get_repository),
) -> list[dict]:
    return repository.list_cards(
        workspace_id=workspace_id,
        card_type=card_type,
        status=status,
        confidence=confidence,
        keyword=keyword,
        tag=tag,
    )


@router.get("/{card_id}")
def get_card(workspace_id: int, card_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    card = repository.get_card(card_id)
    return {
        **card,
        "source_document": repository.get_raw_document(card["source_document_id"]),
        "source_chunk": repository.get_chunk(card["source_chunk_id"]),
        "relations": repository.list_relations(workspace_id, card_id=card_id),
    }


@router.patch("/{card_id}")
def update_card(card_id: int, payload: CardUpdate, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return repository.update_card(card_id=card_id, status=payload.status, tags=payload.tags)


@router.get("/{card_id}/relations")
def list_card_relations(workspace_id: int, card_id: int, repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    return repository.list_relations(workspace_id, card_id=card_id)


@router.get("/{card_id}/paths")
def list_card_paths(
    workspace_id: int,
    card_id: int,
    depth: int = 2,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    try:
        return MultiHopPathService(repository).find_card_paths(
            workspace_id=workspace_id,
            card_id=card_id,
            depth=depth,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
