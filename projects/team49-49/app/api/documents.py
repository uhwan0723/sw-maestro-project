from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.services.extraction import DeterministicCardExtractor, LLMCardExtractor
from app.services.langgraph_remote import RelationLinkingAdapter
from app.services.llm import NoOpLLMClient
from app.services.parsing import parse_document
from app.services.source_connectors import SourceConnectorConfigError, SourceConnectorFetchError, SourceConnectorInputError
from app.workflows.source_intake import SourceIntakeWorkflow
from app.workflows.storage import StorageWorkflow

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])


class TextDocumentCreate(BaseModel):
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_type: str = "manual"
    source_url: str = ""
    external_id: str = ""


class SourceDocumentCreate(BaseModel):
    source_type: str = Field(min_length=1)
    source_url: str = ""
    external_id: str = ""
    title: str = ""
    content: str = ""


def _run_relation_linking(
    request: Request,
    workspace_id: int,
    new_card_ids: list[int],
    repository: SQLiteRepository,
):
    if not new_card_ids:
        return
    adapter = RelationLinkingAdapter(
        remote_runner=getattr(request.app.state, "remote_langgraph_client", None),
    )
    existing_cards = repository.list_cards(workspace_id)
    new_card_id_set = set(new_card_ids)
    new_cards = [c for c in existing_cards if c["id"] in new_card_id_set]

    relations = adapter.run(workspace_id, new_cards, existing_cards)
    for relation in relations:
        repository.create_relation(workspace_id=workspace_id, **relation)


def _normalize_source(
    request: Request,
    workspace_id: int,
    source_type: str,
    title: str,
    content: str,
    source_url: str = "",
    external_id: str = "",
) -> dict:
    workflow = SourceIntakeWorkflow(
        settings=request.app.state.settings,
        connectors=getattr(request.app.state, "source_connector_registry", None),
    )
    return workflow.normalize(
        workspace_id=workspace_id,
        source_type=source_type,
        source_url=source_url,
        external_id=external_id,
        title=title,
        content=content,
    )


def _ingest_normalized_document(
    request: Request,
    normalized: dict,
    repository: SQLiteRepository,
) -> dict:
    workflow = _storage_workflow(request, repository)
    return workflow.ingest_text(
        workspace_id=normalized["workspace_id"],
        filename=normalized["filename"],
        content=normalized["content"],
        source_type=normalized["source_type"],
        source_url=normalized["source_url"],
        external_id=normalized["external_id"],
    )


def _ingest_normalized_tree(
    request: Request,
    normalized: dict,
    repository: SQLiteRepository,
) -> dict:
    result = _ingest_normalized_document(request, normalized, repository)
    result["child_document_ids"] = []
    result["document_link_count"] = 0

    for child in normalized.get("child_documents") or []:
        child_result = _ingest_normalized_tree(request, child, repository)
        repository.create_raw_document_link(
            workspace_id=normalized["workspace_id"],
            source_document_id=result["document_id"],
            target_document_id=child_result["document_id"],
            relation_type="child_page",
            reason="Imported Notion child page",
            confidence="high",
        )

        result["chunk_count"] += child_result.get("chunk_count", 0)
        result["card_count"] += child_result.get("card_count", 0)
        result["skipped_chunk_count"] += child_result.get("skipped_chunk_count", 0)
        result["needs_review_count"] += child_result.get("needs_review_count", 0)
        result["new_card_ids"].extend(child_result.get("new_card_ids", []))
        result["child_document_ids"].append(child_result["document_id"])
        result["child_document_ids"].extend(child_result.get("child_document_ids", []))
        result["document_link_count"] += 1 + child_result.get("document_link_count", 0)

    return result


def _http_error_from_source_error(error: ValueError) -> HTTPException:
    if isinstance(error, SourceConnectorFetchError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    if isinstance(error, (SourceConnectorConfigError, SourceConnectorInputError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/text", status_code=status.HTTP_201_CREATED)
def ingest_text_document(
    request: Request,
    workspace_id: int,
    payload: TextDocumentCreate,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    try:
        normalized = _normalize_source(
            request=request,
            workspace_id=workspace_id,
            source_type=payload.source_type,
            title=payload.filename,
            content=payload.content,
            source_url=payload.source_url,
            external_id=payload.external_id,
        )
        result = _ingest_normalized_tree(request, normalized, repository)
        new_card_ids = result.get("new_card_ids", [])
        _run_relation_linking(request, workspace_id, new_card_ids, repository)
        return result
    except ValueError as error:
        raise _http_error_from_source_error(error) from error


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    workspace_id: int,
    file: UploadFile = File(...),
    source_type: str = Form("upload"),
    source_url: str = Form(""),
    external_id: str = Form(""),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    try:
        text = parse_document(file.filename or "uploaded.txt", await file.read())
        normalized = _normalize_source(
            request=request,
            workspace_id=workspace_id,
            source_type=source_type or "upload",
            title=file.filename or "uploaded.txt",
            content=text,
            source_url=source_url,
            external_id=external_id,
        )
        result = _ingest_normalized_tree(request, normalized, repository)
        new_card_ids = result.get("new_card_ids", [])
        _run_relation_linking(request, workspace_id, new_card_ids, repository)
        return result
    except ValueError as error:
        raise _http_error_from_source_error(error) from error


@router.post("/source", status_code=status.HTTP_201_CREATED)
def ingest_source_document(
    request: Request,
    workspace_id: int,
    payload: SourceDocumentCreate,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    try:
        normalized = _normalize_source(
            request=request,
            workspace_id=workspace_id,
            source_type=payload.source_type,
            title=payload.title,
            content=payload.content,
            source_url=payload.source_url,
            external_id=payload.external_id,
        )
        result = _ingest_normalized_tree(request, normalized, repository)
        new_card_ids = result.get("new_card_ids", [])
        _run_relation_linking(request, workspace_id, new_card_ids, repository)
        return result
    except ValueError as error:
        raise _http_error_from_source_error(error) from error


@router.get("")
def list_documents(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    return repository.list_raw_documents(workspace_id)


@router.get("/{document_id}")
def get_document(workspace_id: int, document_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    document = repository.get_raw_document(document_id)
    if document["workspace_id"] != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _storage_workflow(request: Request, repository: SQLiteRepository) -> StorageWorkflow:
    llm_client = getattr(request.app.state, "llm_client", None)
    if llm_client is None or isinstance(llm_client, NoOpLLMClient):
        return StorageWorkflow(repository)
    return StorageWorkflow(
        repository,
        extractor=LLMCardExtractor(
            llm_client,
            fallback_extractor=DeterministicCardExtractor(),
        ),
    )
