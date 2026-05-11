import os
import requests
import xml.etree.ElementTree as ET

KIPRIS_BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi"


def _get_text(element, tag: str) -> str:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ""


def search_patents(keyword: str, count: int = 30, year: int = 0) -> list[dict]:
    """KIPRIS Plus '특허·실용 공개·등록공보' getWordSearch로 키워드 검색.

    Args:
        keyword: 검색어
        count: 페이지당 건수 (기본 30, 최대 500)
        year: 검색 년도 범위 (0~10, 0=전체)
    """
    api_key = os.getenv("KIPRIS_API_KEY", "")
    url = f"{KIPRIS_BASE_URL}/patUtiModInfoSearchSevice/getWordSearch"
    params = {
        "word": keyword,
        "year": year,
        "patent": "true",
        "utility": "true",
        "numOfRows": min(count, 500),
        "pageNo": 1,
        "ServiceKey": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"KIPRIS API 호출 실패 ({keyword}): {e}")

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise RuntimeError(f"KIPRIS API 응답 파싱 실패: {e}\n응답: {resp.text[:300]}")

    result_code = _get_text(root, ".//resultCode")
    if result_code and result_code not in ("00", "0"):
        result_msg = _get_text(root, ".//resultMsg")
        raise RuntimeError(f"KIPRIS API 오류 (코드={result_code}): {result_msg}")

    patents = []
    for item in root.findall(".//item"):
        patent = {
            "application_number": _get_text(item, "applicationNumber"),
            "title": _get_text(item, "inventionTitle"),
            "applicant": _get_text(item, "applicantName"),
            "open_date": _get_text(item, "openDate"),
            "register_status": _get_text(item, "registerStatus"),
            "abstract": _get_text(item, "astrtCont"),
            "ipc_code": _get_text(item, "ipcNumber"),
        }
        if patent["application_number"] and patent["title"]:
            patents.append(patent)

    return patents


def search_patents_multi(keywords: list[str], count_per_keyword: int = 30) -> list[dict]:
    """여러 키워드로 검색 후 중복 제거해서 반환."""
    all_patents: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []

    for keyword in keywords[:3]:
        try:
            patents = search_patents(keyword, count=count_per_keyword)
            for p in patents:
                if p["application_number"] not in seen:
                    seen.add(p["application_number"])
                    all_patents.append(p)
        except RuntimeError as e:
            errors.append(str(e))

    if not all_patents and errors:
        raise RuntimeError("\n".join(errors))

    return all_patents


def get_patent_detail(application_number: str) -> dict:
    """출원번호로 서지상세정보 조회 (getBibliographyDetailInfoSearch).

    초록/청구항이 getWordSearch 응답에 없을 때 보강용으로 사용.
    """
    api_key = os.getenv("KIPRIS_API_KEY", "")
    url = f"{KIPRIS_BASE_URL}/patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch"
    params = {
        "applicationNumber": application_number,
        "ServiceKey": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError) as e:
        raise RuntimeError(f"KIPRIS 상세조회 실패 ({application_number}): {e}")

    item = root.find(".//item")
    if item is None:
        return {}

    return {
        "application_number": application_number,
        "title": _get_text(item, ".//inventionTitle") or _get_text(item, ".//biblioSummaryInfoArray/biblioSummaryInfo/inventionTitle"),
        "abstract": _get_text(item, ".//abstractInfoArray/abstractInfo/astrtCont") or _get_text(item, ".//astrtCont"),
        "claim": _get_text(item, ".//claimInfoArray/claimInfo/claim"),
    }


def get_representative_image(application_number: str) -> dict:
    """출원번호로 대표도면 이미지 URL 조회 (getReprsntFloorPlanInfoSearch).

    Returns:
        {'doc_name': str, 'path': str, 'large_path': str}
        조회 실패하거나 이미지 없으면 모든 값이 빈 문자열.
    """
    api_key = os.getenv("KIPRIS_API_KEY", "")
    url = f"{KIPRIS_BASE_URL}/patUtiModInfoSearchSevice/getReprsntFloorPlanInfoSearch"
    params = {
        "applicationNumber": application_number,
        "ServiceKey": api_key,
    }

    empty = {"doc_name": "", "path": "", "large_path": ""}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError):
        return empty

    info = root.find(".//imagePathInfo")
    if info is None:
        return empty

    return {
        "doc_name": _get_text(info, "docName"),
        "path": _get_text(info, "path"),
        "large_path": _get_text(info, "largePath"),
    }


def fetch_image_as_base64(image_url: str) -> str:
    """이미지 URL을 받아 base64 데이터 URI 문자열로 반환.

    KIPRIS의 fileToss.jsp가 application/octet-stream으로 응답하므로,
    안정적 표시 위해 인라인 base64로 변환.
    실패 시 빈 문자열 반환.
    """
    if not image_url:
        return ""
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        data = resp.content
        if not data:
            return ""
        # JPEG 매직넘버 확인 (FFD8FF)
        mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png" if data[:8].startswith(b"\x89PNG") else "image/jpeg"
        import base64 as _b64
        encoded = _b64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except requests.RequestException:
        return ""
