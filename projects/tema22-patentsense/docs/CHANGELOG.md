# PatentSense 변경 이력

## feat/preprocess-idea 브랜치 (진행중)

### 1. LLM 아이디어 전처리 노드 추가

**변경 파일**: `agent/graph.py`, `agent/prompts.py`, `app.py`

**내용**:
- `preprocess_idea` 노드 추가
- 사용자가 입력한 자연어를 LLM이 특허 검색에 최적화된 기술 용어로 변환
- 변환 결과를 키워드 추출 및 임베딩 유사도 계산에 활용

**전처리 결과 3가지**:
- `core_technology`: 핵심 기술 원리 한 문장
- `tech_components`: 기술 구성요소 목록
- `search_query`: KIPRIS 검색 최적화 문장

**예시**:
```
입력: "음성으로 집 안의 조명과 에어컨을 제어하는 스마트홈"

전처리 결과:
- 핵심 기술: 음성인식 신호처리 기반 가전기기 무선 제어
- 기술 구성요소: 음성인식 모듈, IoT 조명 제어 시스템, 음성 명령 기반 공조 제어 알고리즘
- 검색어: 음성인식 IoT 조명 공조 제어 시스템 및 방법
```

---

### 2. KIPRIS 검색어 개선

**변경 파일**: `agent/graph.py`

**내용**:
- 기존: LLM이 추출한 키워드로 검색
- 변경: 전처리된 `tech_components`(기술 구성요소)로 검색
- 더 정확한 기술 용어로 KIPRIS 검색 → 관련성 높은 특허 수집

---

### 3. 청구항 기반 유사도 재랭킹

**변경 파일**: `agent/graph.py`

**내용**:
- 기존: 제목 + 초록으로 유사도 계산 → Top 5
- 변경: 2단계 랭킹
  1. 제목 + 초록으로 1차 유사도 계산 → Top 15 선정
  2. Top 15 청구항 조회 후 제목 + 초록 + 청구항으로 재계산 → 최종 Top 5

**청구항을 쓰는 이유**:
- 청구항은 특허에서 법적으로 보호받는 기술 범위를 정의
- 제목/초록보다 핵심 기술 내용이 구체적으로 담겨있어 유사도 정확도 향상

---

### 4. Tool 기반 구조로 전환 (A안)

**변경 파일**: `agent/graph.py`, `tools/patent_tools.py` (신규)

**내용**:
- 외부 API 호출과 임베딩을 LangGraph Tool로 등록
- 노드 내부에서 직접 함수 호출 → `.invoke()` tool 호출로 교체
- Agentic Workflow 구조가 명확하게 보임

**등록된 Tool 목록**:

| Tool | 역할 |
|------|------|
| `search_patent_tool` | KIPRIS 특허 검색 |
| `get_claim_tool` | 특허 청구항 조회 |
| `get_representative_image_tool` | 대표도면 URL 조회 |
| `fetch_image_tool` | 이미지 base64 변환 |
| `embed_query_tool` | 아이디어 텍스트 임베딩 |
| `embed_passage_tool` | 특허 텍스트 임베딩 |

**현재 구조 (A안)**:
```
노드 순서 고정 (파이프라인 유지)
외부 호출만 tool 형태로 감쌈
→ agentic 구조가 보이지만 피드백 루프는 없음
```

---

### 5. UI 개선

**변경 파일**: `app.py`

**내용**:
- 전처리 결과를 리포트 상단에 표로 표시
  - 💡 핵심 기술
  - 🔧 기술 구성요소
  - 🔎 검색어
- 입력창 안내 문구 변경: "아이디어를 한 문장 이상 구체적으로 입력하세요..."
- 사용 방법에 구체적 입력 안내 추가

---

## 전체 노드 흐름 (현재)

```
사용자 입력
    ↓
preprocess_idea        ← LLM: 자연어 → 기술 용어 변환
    ↓
extract_keywords       ← LLM: 검색 키워드 추출 (보조)
    ↓
search_patents         ← tool: tech_components로 KIPRIS 검색
    ↓
rank_by_similarity     ← tool: 임베딩 유사도 계산 + 청구항 재랭킹
    ↓
analyze_conflicts      ← LLM: 충돌 요소 분석
    ↓
derive_differentiators ← LLM: 차별화 전략 도출
    ↓
generate_report        ← LLM: 최종 리포트 생성
```

## LLM 호출 횟수 (1회 실행 기준)

| 단계 | 호출 수 |
|------|--------|
| 전처리 (LLM) | 1회 |
| 키워드 추출 (LLM) | 1회 |
| 임베딩 1차 (특허 최대 30개) | 최대 31회 |
| 청구항 조회 (API) | 최대 15회 |
| 임베딩 2차 (Top 15 재랭킹) | 15회 |
| 충돌 분석 (LLM) | 1회 |
| 차별화 전략 (LLM) | 1회 |
| 리포트 생성 (LLM) | 1회 |
| **총** | **LLM 5회 + 임베딩 최대 46회 + API 15회** |
