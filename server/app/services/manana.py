import logging
from urllib.parse import quote

import requests
from flask import current_app

logger = logging.getLogger(__name__)

SUPPORTED_BRANDS = ("tj", "kumyoung")

SEARCH_TYPES = ("song", "singer")


class MananaError(Exception):
    pass


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

    if not isinstance(payload, list):
        logger.warning("예상치 못한 manana 응답 형식 (%s): %r", url, type(payload))
        return []

    return payload


def _encode(value):
    return quote(str(value).strip(), safe="")


def search(keyword, search_type="song", brand=None):
    if search_type not in SEARCH_TYPES:
        raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

    path = f"/karaoke/{search_type}/{_encode(keyword)}"
    if brand:
        path += f"/{_encode(brand)}"

    return _request(f"{path}.json")
