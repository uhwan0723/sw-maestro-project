# Legal AI Agent — Backend

교통 법률 상담 AI 에이전트 백엔드 (FastAPI + LangGraph + FAISS).

**스코프: 교통 도메인 전용** — 뺑소니, 음주운전, 보행자사고, 역주행·중앙선침범, 난폭운전.

## 파트 분담

| 파트 | 담당 | 영역 |
|---|---|---|
| A | LLM | `app/agents/{classify,clarify,generate}.py`, `app/llm/solar_client.py`, `app/utils/{citation_extractor,keyword_fallback,prompt_loader}.py`, `app/prompts/`, `app/taxonomy.py` |
| B | 검색 | `app/agents/retrieve.py`, `app/retrieval/`(예정), `data/raw/`, `data/indices/`, `scripts/build_index.py`(예정) |
| C | 로직·통합 | `app/agents/{guide,settlement,post_check,fallback}.py`, `app/graph.py`, `app/state.py`, `app/api/`, `app/config.py`, `app/constants.py`, `data/guides.yaml`, 통합 테스트 |

현재 mock 상태:
- A 본구현 완료 (Upstage Solar 연동)
- B mock — `app/agents/retrieve.py` 가 case_type 기준 하드코딩 dict 반환
- C 본구현 완료

## 실행

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
# .env 의 UPSTAGE_API_KEY 설정 (https://console.upstage.ai/api-keys)

# 벡터 스토어 구축 (법령 및 판례 데이터 임베딩)
python build_vector_store.py

uvicorn app.api.main:app --reload --port 8000
```

## 엔드포인트

- `GET  /healthz` — 헬스 체크
- `POST /chat` — SSE 스트리밍 (`meta`, `token`, `state`, `done`, `error`)
- `POST /chat/sync` — 비스트리밍 디버그용

요청:
```json
{
  "user_query": "음주운전 단속됐어요",
  "session_id": "optional-uuid",
  "history": []
}
```

## 그래프 흐름

```
classify ─┬─ case_type == "OUT_OF_SCOPE"           → fallback_no_domain → fallback → END
          ├─ classification_confidence < 0.4       → clarify → END
          └─ retrieve ─┬─ docs == []               → fallback_no_docs → fallback → END
                       └─ guide → settlement → generate → post_check → END
```

## case_type enum

```
HIT_AND_RUN          뺑소니
WRONG_WAY_DRIVING    역주행·중앙선침범
DRUNK_DRIVING        음주운전
PEDESTRIAN_ACCIDENT  보행자사고
RECKLESS_DRIVING     난폭운전·안전운전위반
OUT_OF_SCOPE         교통 무관
```

## State 계약 (`app/state.py`)

LegalState 의 필드가 3 파트 인터페이스. 변경 시 합의 필수.

`RetrievedDoc` 키 (B → A·C 계약):
`{doc_id, type, title, content, case_types, score, settlement_amount}`

`type ∈ {"법령","판례","사례"}`. `type=="사례"` 일 때 `settlement_amount` (int, KRW) 필요.

## 테스트

```bash
pytest tests/ -v
```

| 파일 | 영역 | 내용 |
|---|---|---|
| `tests/test_classify.py` | A | 분류 정확도 80%, OOS, 폴백, 신뢰도 임계 |
| `tests/test_generate.py` | A | 인용 마커, 면책 고지, 환각 방지, 폴백 |
| `tests/test_citation.py` | A | 인용 추출 단위 테스트 |
| `tests/test_graph.py` | C | end-to-end 그래프 통합 (Solar mock) |

## CLI 스크립트

```bash
python scripts/hello_upstage.py            # API 키·연결 검증
python -m scripts.run_classify "음주운전"   # 분류 단독 실행
python -m scripts.run_generate              # 답변 생성 단독 실행 (mock 입력)
python -m scripts.eval_classify             # 평가셋 10개 정확도 측정
```

## 주요 상수 (`app/constants.py`)

| 상수 | 값 | 설명 |
|---|---|---|
| `CLARIFY_THRESHOLD` | 0.4 | confidence < 임계 → clarify 분기 |
| `MAX_CONTEXT_DOCS` | 5 | generate 에 넘길 docs 최대 개수 |
| `MAX_HISTORY_TURNS` | 6 | 답변 컨텍스트로 포함할 최근 대화 턴 |
| `LLM_CLASSIFY_MODEL` | `solar-mini` | Upstage Solar mini |
| `LLM_GENERATE_MODEL` | `solar-pro` | Upstage Solar Pro |

## 배포 메모

- Vercel serverless 는 SSE 타임아웃 짧음 → BE 는 Railway / Fly / Render 등 별도 호스팅.
- FAISS 인덱스 (B 본구현 후) + 임베딩 메모리 약 2GB. 무료 티어 빠듯.
- 인덱스 파일은 git 미포함. 다운로드 스크립트 별도 (B 담당).
