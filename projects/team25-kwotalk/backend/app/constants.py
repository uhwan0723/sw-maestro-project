"""LLM·정책 상수.

- LLM_*_MODEL: Upstage Solar 모델 ID. 정책 변경 시 여기만 수정.
- CLARIFY_THRESHOLD: 분류 신뢰도 미달 시 clarify 분기 임계값.
- DISCLAIMER: 답변 말미 강제 면책 고지.
"""

CLARIFY_THRESHOLD = 0.4
MAX_CONTEXT_DOCS = 5
MAX_HISTORY_TURNS = 6

LLM_CLASSIFY_MODEL = "solar-mini"
LLM_GENERATE_MODEL = "solar-pro"

DISCLAIMER = "※ 본 답변은 일반적인 정보 제공이며 법적 효력이 없습니다. 구체적인 사안은 반드시 변호사 상담을 권장합니다."
