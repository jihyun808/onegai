"""manana 비공식 노래방 API 클라이언트.

엔드포인트:
    /karaoke/song/{q}.json                 곡명 검색
    /karaoke/song/{q}/{brand}.json         곡명 + 브랜드
    /karaoke/singer/{q}.json               가수 검색
    /karaoke/singer/{q}/{brand}.json       가수 + 브랜드
"""

import logging
from urllib.parse import quote

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# 한국 노래방에서 일본곡을 찾는 것이 기획 의도이므로 국내 기기만 노출한다.
# manana API 자체는 joysound / dam (일본 기기)도 지원한다.
SUPPORTED_BRANDS = ("tj", "kumyoung")

SEARCH_TYPES = ("song", "singer")


class MananaError(Exception):
    """manana API 호출 실패."""


def _request(path):
    base_url = current_app.config["MANANA_BASE_URL"].rstrip("/")
    timeout = current_app.config["MANANA_TIMEOUT"]
    url = f"{base_url}{path}"

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise MananaError("manana API 응답 시간이 초과되었습니다.") from exc
    except requests.RequestException as exc:
        raise MananaError("manana API 호출에 실패했습니다.") from exc
    except ValueError as exc:
        raise MananaError("manana API 응답을 해석할 수 없습니다.") from exc

    # 정상 응답은 리스트, 결과 없음도 빈 리스트로 온다.
    if not isinstance(payload, list):
        logger.warning("예상치 못한 manana 응답 형식 (%s): %r", url, type(payload))
        return []

    return payload


def _encode(value):
    # 경로 세그먼트이므로 '/' 까지 인코딩한다.
    return quote(str(value).strip(), safe="")


def search(keyword, search_type="song", brand=None):
    """곡명 또는 가수명으로 검색한다. brand가 None이면 전체 브랜드."""
    if search_type not in SEARCH_TYPES:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    path = f"/karaoke/{search_type}/{_encode(keyword)}"
    if brand:
        path += f"/{_encode(brand)}"

    return _request(f"{path}.json")

