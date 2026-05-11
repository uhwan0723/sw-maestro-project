"""사용자 설정 폼의 옵션. 한 곳에서만 관리한다.

도시/카테고리는 백엔드에 enum이 없어 FE에서 정의하고, 날씨 에이전트·뉴스 에이전트와 합의한다.
"""

# 백엔드 weather 모듈의 CITY_NAME_MAP에 매핑된 도시만 노출한다.
CITY_OPTIONS: list[str] = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "제주",
]

# 뉴스 에이전트와 합의 필요. NewsAPI/네이버 뉴스 카테고리 매핑 테이블 공유.
CATEGORY_OPTIONS: list[str] = [
    "IT", "경제", "사회", "문화", "정치", "스포츠",
]

# 백엔드 BriefingRequest.length의 기본값. UI에는 노출하지 않고 고정으로 사용한다.
DEFAULT_LENGTH: str = "medium"
