from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.consultation import (
    ConsultationResponse,
    ConsultationStartResponse,
    UserConsultationRequest,
)
from app.workflow.state import build_consultation_response, build_initial_state

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.post("", response_model=ConsultationStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_consultation(
    payload: UserConsultationRequest,
    request: Request,
) -> ConsultationStartResponse:
    store = request.app.state.store
    broker = request.app.state.broker
    runner = request.app.state.workflow_runner

    existing = await store.get(payload.consultation_id)
    if existing is not None:
        return ConsultationStartResponse(
            consultation_id=existing.consultation_id,
            status=existing.status,
        )

    state = build_initial_state(payload)
    await store.create(state)
    await broker.publish(
        state.consultation_id,
        "status_changed",
        {"status": state.status.value},
    )

    task = asyncio.create_task(
        runner.run(state.consultation_id, state.model_dump(mode="json")),
        name=f"consultation-{state.consultation_id}",
    )
    request.app.state.running_tasks.add(task)
    task.add_done_callback(request.app.state.running_tasks.discard)

    return ConsultationStartResponse(
        consultation_id=state.consultation_id,
        status=state.status,
    )


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(consultation_id: str, request: Request) -> ConsultationResponse:
    state = await request.app.state.store.get(consultation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="consultation not found")
    return build_consultation_response(state)
