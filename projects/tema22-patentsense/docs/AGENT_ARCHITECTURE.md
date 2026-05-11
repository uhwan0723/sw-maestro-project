# PatentSense Agent 아키텍처 비교

## 현재 구조: 순차적 파이프라인 (Sequential Pipeline)

### 개념
노드들이 정해진 순서대로 실행되는 구조. agent가 판단하지 않고 항상 같은 순서로 실행됨.

### 흐름
```
사용자 입력
    ↓
preprocess_idea     → LLM이 아이디어를 기술 용어로 변환
    ↓
extract_keywords    → LLM이 검색 키워드 추출
    ↓
search_patents      → KIPRIS API 호출해서 특허 수집
    ↓
rank_by_similarity  → Solar 임베딩으로 유사도 계산 + 청구항 재랭킹
    ↓
analyze_conflicts   → LLM이 충돌 요소 분석
    ↓
derive_differentiators → LLM이 차별화 전략 도출
    ↓
generate_report     → LLM이 최종 리포트 생성
```

### 코드 구조
```python
# graph.py
g.add_node("preprocess_idea", preprocess_idea)
g.add_node("extract_keywords", extract_keywords)
g.add_node("search_patents", search_patents)
...

# 엣지가 고정되어 있음
g.add_edge("preprocess_idea", "extract_keywords")
g.add_edge("extract_keywords", "search_patents")
g.add_edge("search_patents", "rank_by_similarity")
...
```

### 특징
- ✅ 구조가 단순하고 예측 가능
- ✅ 디버깅 쉬움
- ✅ 속도 일정
- ❌ 항상 같은 순서로 실행 (유연성 없음)
- ❌ 결과가 별로면 다시 검색하거나 보완하는 게 불가능
- ❌ agentic 이라고 보기 어려움 (그냥 함수 파이프라인)

---

## 변경 구조 A: Tool 기반 (작은 변경)

### 개념
기존 노드 구조는 유지하되, KIPRIS 검색/임베딩 같은 외부 호출을 LangGraph Tool로 등록.
agent가 tool을 호출하는 형태가 명확하게 보임.

### 흐름
```
사용자 입력
    ↓
agent (LLM)
    ├── tool 호출: preprocess_tool(아이디어)
    ├── tool 호출: search_patent_tool(키워드)
    ├── tool 호출: embed_tool(텍스트)
    ├── tool 호출: get_claim_tool(출원번호)
    └── tool 호출: generate_report_tool(특허 목록)
    ↓
최종 리포트
```

### 코드 구조
```python
from langchain_core.tools import tool

@tool
def search_patent_tool(keyword: str) -> list:
    """KIPRIS에서 특허를 검색합니다."""
    return search_patents(keyword, count=10)

@tool
def get_claim_tool(application_number: str) -> str:
    """특허 청구항을 가져옵니다."""
    detail = get_patent_detail(application_number)
    return detail.get("claim", "")

@tool
def embed_tool(text: str) -> list:
    """텍스트를 임베딩 벡터로 변환합니다."""
    return _embed(text, model="embedding-passage")
```

### 특징
- ✅ tool 형태라 agentic workflow가 명확하게 보임
- ✅ 기존 로직 재사용 가능
- ✅ 변경 범위가 작음 (1~2일 작업)
- ❌ 실행 순서는 여전히 고정에 가까움
- ❌ agent가 스스로 판단하는 건 아님

---

## 변경 구조 B: 완전한 Agentic 구조 (큰 변경)

### 개념
LLM agent가 상황을 보고 어떤 tool을 쓸지 스스로 결정. 결과가 부족하면 추가 검색하거나 다른 tool을 호출하는 진짜 agentic 구조.

### 흐름
```
사용자 입력
    ↓
agent (LLM) ←─────────────────────────────┐
    │                                      │
    ├── "키워드가 필요해"                    │
    │   → search_patent_tool("음성인식")    │
    │   → 결과 30개 받음                   │
    │                                      │
    ├── "유사도 계산이 필요해"               │
    │   → embed_tool("특허 텍스트")         │
    │   → 유사도 계산                       │
    │                                      │
    ├── "청구항이 없는 특허가 있어"           │
    │   → get_claim_tool("출원번호")        │ (부족하면 다시)
    │                                      │
    ├── "검색 결과가 부족해 추가 검색 필요"   │
    │   → search_patent_tool("IoT 조명")   ─┘
    │
    └── "충분해, 리포트 생성"
        → generate_report_tool(...)
        ↓
    최종 리포트
```

### 코드 구조
```python
from langgraph.prebuilt import create_react_agent

tools = [
    search_patent_tool,
    embed_tool,
    get_claim_tool,
    analyze_conflict_tool,
    generate_report_tool,
]

# agent가 tool을 스스로 선택
agent = create_react_agent(llm, tools)
```

### 특징
- ✅ 진짜 agentic workflow
- ✅ 결과 부족하면 스스로 추가 검색
- ✅ 상황에 따라 유연하게 대응
- ❌ 실행 순서가 예측 불가 (디버깅 어려움)
- ❌ LLM이 잘못된 tool 선택할 수 있음
- ❌ 구현 복잡하고 시간 많이 걸림 (1주일+)
- ❌ API 비용 증가 (LLM 판단 횟수 늘어남)

---

## 비교 요약

| 항목 | 현재 (파이프라인) | A (Tool 기반) | B (완전 Agentic) |
|------|-----------------|--------------|-----------------|
| 구현 난이도 | ✅ 쉬움 | ✅ 보통 | ❌ 어려움 |
| Agentic 느낌 | ❌ 약함 | 🟡 중간 | ✅ 강함 |
| 유연성 | ❌ 낮음 | 🟡 중간 | ✅ 높음 |
| 예측 가능성 | ✅ 높음 | ✅ 높음 | ❌ 낮음 |
| 속도 | ✅ 일정 | ✅ 일정 | ❌ 불규칙 |
| API 비용 | ✅ 낮음 | ✅ 낮음 | ❌ 높음 |
| 작업 기간 | - | 1~2일 | 1주일+ |

---

## 권장사항

지금 단계에서는 **A안 (Tool 기반)** 이 현실적.

- 기존 로직 유지하면서 tool 형태만 추가
- agentic workflow가 명확하게 보임
- 구현 빠름

B안은 나중에 서비스가 더 성숙해지면 고려.
