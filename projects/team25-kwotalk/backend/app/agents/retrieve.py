"""FAISS 기반 retrieve_node 구현.

계약: retrieved_docs 원소는 RetrievedDoc 스키마 준수.
스코프: 교통 도메인 전용. user_query 기반 벡터 검색.
"""
import json
import os
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.state import LegalState

# 전역 변수로 모델과 인덱스 로드 (모듈 로드 시 한 번만)
_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dbvector", "law_index.faiss")
_METADATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dbvector", "law_metadata.json")

_model = None
_index = None
_metadata = None


def _load_resources():
    global _model, _index, _metadata
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    if _index is None and os.path.exists(_INDEX_PATH):
        _index = faiss.read_index(_INDEX_PATH)
    if _metadata is None and os.path.exists(_METADATA_PATH):
        with open(_METADATA_PATH, "r", encoding="utf-8") as f:
            _metadata = json.load(f)


def _search_faiss(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if _index is None or _metadata is None:
        return []
    
    # 쿼리 임베딩
    query_embedding = _model.encode([query], convert_to_numpy=True)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)  # 정규화
    
    # 검색
    scores, indices = _index.search(query_embedding, top_k)
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:  # 유효하지 않은 인덱스
            continue
        meta = _metadata[idx]
        results.append({
            "doc_id": str(meta["id"]),
            "type": meta.get("type", "법령"),  # 메타데이터에서 type 가져오기
            "title": meta.get("title", ""),
            "content": meta.get("summary", ""),
            "case_types": meta.get("keywords", []),  # keywords를 case_types로 사용
            "score": float(score),
            "settlement_amount": None,  # 기본값
        })
    return results


async def retrieve_node(state: LegalState) -> dict:
    _load_resources()
    
    user_query = state.get("user_query", "")
    if not user_query:
        return {"retrieved_docs": []}
    
    retrieved_docs = _search_faiss(user_query, top_k=5)
    return {"retrieved_docs": retrieved_docs}
