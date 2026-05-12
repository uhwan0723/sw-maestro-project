from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from app.repositories.sqlite import SQLiteRepository
from app.services.context_bundle import build_qa_context_bundle
from app.services.qa_engine import INSUFFICIENT_CONTEXT_MESSAGE, LocalQAEngine
from app.services.retrieval import RetrievalService


class QAInput(BaseModel):
    workspace_id: int = Field(..., ge=1, description="Workspace id to query.")
    question: str = Field(..., min_length=1, description="Question to answer from stored context.")


class QAStudioContext(BaseModel):
    answer_mode: Literal["llm", "extractive"] = Field(
        "llm",
        description="Use llm for Upstage-backed JSON answers, or extractive for local evidence-only runs.",
    )
    top_k: int = Field(4, ge=1, le=12, description="Number of cards and chunks to retrieve.")
    model: str = Field("solar-pro2", description="Upstage chat model name used in llm mode.")
    system_prompt: str = Field(
        "",
        description="Optional system prompt override for llm mode. Empty keeps the built-in grounded QA prompt.",
    )
    temperature: float = Field(0.2, ge=0.0, le=1.0, description="LLM sampling temperature.")
    max_tokens: int = Field(900, ge=128, le=4000, description="Maximum LLM output tokens.")


class QAState(TypedDict, total=False):
    workspace_id: int
    question: str
    search: dict[str, list[dict[str, Any]]]

    # expand_context 출력
    cards: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    neighbor_cards: list[dict[str, Any]]
    evidence_cards: list[dict[str, Any]]
    evidence_chunks: list[dict[str, Any]]
    relation_evidence: list[dict[str, Any]]

    # format_context 출력
    context_str: str

    # generate_answer 출력
    answer: str
    cited_card_ids: list[int]
    cited_chunk_ids: list[int]

    # assess_and_finalize 출력
    confidence: str
    missing_evidence: list[str]


class RetrievalQAWorkflow:
    def __init__(
        self,
        repository: SQLiteRepository,
        upstage_api_key: str = "",
    ):
        self.repository = repository
        self.retrieval = RetrievalService(repository)
        self.engine = LocalQAEngine(repository, upstage_api_key)
        self.graph = self._build_graph()

    def answer(self, workspace_id: int, question: str) -> dict:
        state = self.graph.invoke({"workspace_id": workspace_id, "question": question})

        answer = state.get("answer", INSUFFICIENT_CONTEXT_MESSAGE)
        cards = state.get("cards") or []
        chunks = state.get("chunks") or []

        self.repository.create_chat_history(
            workspace_id=workspace_id,
            question=question,
            answer=answer,
            referenced_card_ids=[c["id"] for c in cards],
            referenced_chunk_ids=[c["id"] for c in chunks],
        )
        return {
            "answer": answer,
            "confidence": state.get("confidence", "low"),
            "evidence_cards": state.get("evidence_cards") or [],
            "evidence_chunks": state.get("evidence_chunks") or [],
            "relation_evidence": state.get("relation_evidence") or [],
            "missing_evidence": state.get("missing_evidence") or [],
        }

    def _build_graph(self):
        graph = StateGraph(QAState, context_schema=QAStudioContext, input_schema=QAInput)
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("expand_context", self._expand_context)
        graph.add_node("format_context", self._format_context)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_node("assess_and_finalize", self._assess_and_finalize)
        graph.add_edge(START, "retrieve_context")
        graph.add_edge("retrieve_context", "expand_context")
        graph.add_conditional_edges(
            "expand_context",
            lambda s: "format_context" if (s.get("cards") or s.get("chunks")) else END,
        )
        graph.add_edge("format_context", "generate_answer")
        graph.add_edge("generate_answer", "assess_and_finalize")
        graph.add_edge("assess_and_finalize", END)
        return graph.compile()

    @staticmethod
    def _runtime_context(runtime: Runtime[QAStudioContext]) -> QAStudioContext:
        context = runtime.context
        if isinstance(context, QAStudioContext):
            return context
        if isinstance(context, dict):
            return QAStudioContext.model_validate(context)
        return QAStudioContext()

    def _retrieve_context(
        self,
        state: QAState,
        runtime: Runtime[QAStudioContext],
    ) -> QAState:
        context = self._runtime_context(runtime)
        return {
            "search": self.retrieval.search(
                workspace_id=state["workspace_id"],
                query=state["question"],
                top_k=context.top_k,
            )
        }

    def _expand_context(self, state: QAState) -> QAState:
        search = state.get("search") or {}
        cards = search.get("cards") or []
        chunks = search.get("chunks") or []

        if not cards and not chunks:
            return {
                "cards": [],
                "chunks": [],
                "relations": [],
                "neighbor_cards": [],
                "evidence_cards": [],
                "evidence_chunks": [],
                "relation_evidence": [],
                "answer": INSUFFICIENT_CONTEXT_MESSAGE,
                "confidence": "low",
                "missing_evidence": ["질문과 관련된 저장 컨텍스트가 부족합니다."],
            }

        card_ids = [c["id"] for c in cards]
        expansion = self.retrieval.expand_with_neighbor_cards(state["workspace_id"], card_ids)
        bundle = build_qa_context_bundle(
            workspace_id=state["workspace_id"],
            question=state["question"],
            cards=cards,
            chunks=chunks,
            relations=expansion["relations"],
            neighbor_cards=expansion["neighbor_cards"],
        )
        return {
            "cards": bundle["cards"],
            "chunks": bundle["chunks"],
            "relations": bundle["relations"],
            "neighbor_cards": bundle["neighbor_cards"],
            "evidence_cards": [self.engine.card_evidence(c) for c in cards],
            "evidence_chunks": [self.engine.chunk_evidence(c) for c in chunks],
            "relation_evidence": [self.engine.relation_evidence(r) for r in expansion["relations"]],
        }

    def _format_context(self, state: QAState) -> QAState:
        return {
            "context_str": self.engine.format_context(
                state.get("cards") or [],
                state.get("chunks") or [],
                state.get("relations") or [],
                state.get("neighbor_cards") or [],
            )
        }

    def _generate_answer(
        self,
        state: QAState,
        runtime: Runtime[QAStudioContext],
    ) -> QAState:
        context = self._runtime_context(runtime)
        if context.answer_mode == "extractive":
            return self.engine.generate_extractive_answer(
                state.get("question", ""),
                state.get("cards") or [],
                state.get("chunks") or [],
            )
        return self.engine.generate_answer(
            state.get("question", ""),
            state.get("context_str", ""),
            system_prompt=context.system_prompt,
            model=context.model,
            temperature=context.temperature,
            max_tokens=context.max_tokens,
        )

    def _assess_and_finalize(self, state: QAState) -> QAState:
        confidence, missing = self.engine.assess_confidence(
            state.get("cards") or [],
            state.get("cited_card_ids") or [],
        )
        return {
            "confidence": confidence,
            "missing_evidence": missing,
        }
