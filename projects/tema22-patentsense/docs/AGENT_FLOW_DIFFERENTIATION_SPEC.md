# Agent Flow Differentiation Spec (MVP+)

## 1) 목표
기존 "키워드 추출 → 특허 검색 → 유사도 계산 → 리포트" 파이프라인을 **에이전트 플로우**로 확장해,
- 차별화 포인트를 명시적으로 도출하고
- 명세서 초안(기술 구성요소/청구항 초안 관점)을 생성하며
- 사용자에게 다음 행동까지 안내하는 시스템으로 발전시킨다.

## 2) 현재 베이스라인
현재 그래프 노드:
1. `extract_keywords`
2. `search_patents`
3. `rank_by_similarity`
4. `generate_report`

강점:
- 검색-랭킹-요약의 기본 루프가 이미 동작함
- KIPRIS + 임베딩 점수로 정량 근거가 있음

갭:
- 아이디어가 넓을 때 추가 질의 루프가 없음
- "왜 충돌하는지"를 구조적으로 분해하는 단계가 약함
- 차별화 전략/명세서 초안이 별도 산출물로 분리되지 않음

## 3) 제안 Agent Flow
### 3.1 노드 구성(확장)
1. `structure_idea`
   - 자유 입력을 기술 블록(문제/핵심구성/동작/효과)으로 구조화
2. `extract_keywords`
   - 구조화 결과 기반 키워드 추출
3. `search_patents`
   - KIPRIS 검색 + 중복 제거
4. `score_similarity`
   - 임베딩 점수 계산(0~100 정규화)
5. `analyze_conflicts`
   - Top 특허와 아이디어 간 충돌 요소(구성/동작/효과) 추출
6. `derive_differentiators`
   - 충돌 요소를 피하는 차별화 옵션 2~3개 생성
7. `draft_spec_outline`
   - 명세서 작성용 초안(발명의 배경/해결과제/구성/효과) 생성
8. `generate_report`
   - 최종 사용자 리포트(위험도/근거/다음 액션/면책)

### 3.2 조건부 분기
- 입력이 과도하게 포괄적이면 `ask_clarifying_question` 노드로 분기
- KIPRIS 실패 시 재시도 안내 + 부분 결과 반환
- 유사 특허 없음 시 임의 결론 생성 금지, 검색 확장 전략 제시

## 4) 차별화 포인트(대외 메시지)
1. 단순 유사도 나열이 아닌 **충돌 요소 분해 분석**
2. 분석 결과를 바로 실행 가능한 **차별화 옵션**으로 변환
3. 데모 단계에서도 바로 쓸 수 있는 **명세서 초안 구조 출력**

## 5) 출력 스키마(초안)
```json
{
  "risk_level": "low|medium|high",
  "top_patents": [
    {
      "application_number": "string",
      "title": "string",
      "score": 72.4,
      "conflicts": ["구성요소 A 중복", "동작 절차 B 유사"]
    }
  ],
  "differentiators": [
    "차별화 전략 1",
    "차별화 전략 2"
  ],
  "spec_outline": {
    "background": "...",
    "problem": "...",
    "solution": "...",
    "effects": ["..."]
  },
  "disclaimer": "본 분석은 참고용이며 최종 법적 판단은 전문가와 상담하세요."
}
```

## 6) 구현 순서(권장)
### Phase 1 (빠른 실험)
- `structure_idea`, `analyze_conflicts`, `derive_differentiators` 노드 추가
- 기존 `generate_report`를 확장해 차별화 섹션 포함

### Phase 2 (명세서 초안 강화)
- `draft_spec_outline` 노드 추가
- 출력 스키마 기반 구조화된 결과 반환

### Phase 3 (품질/신뢰성)
- 입력 모호성 분기(`ask_clarifying_question`)
- 실패/빈결과 처리 시나리오 테스트 보강

## 7) 완료 기준(DoD)
- E2E에서 "유사 특허 + 충돌요소 + 차별화전략 + 명세서 초안"이 한 번에 출력된다.
- 유사 특허 없음/외부 API 실패 시에도 임의 결과 없이 안내가 반환된다.
- 결과에 법적 면책 문구가 항상 포함된다.
- 커밋/브랜치 규칙과 보안 규칙(.env, 키 비노출)을 준수한다.
