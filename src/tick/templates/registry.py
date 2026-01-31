from __future__ import annotations

_TEMPLATE_MAP = {
    "web": "web_general.yaml",
    "api": "api_general.yaml",
    "accessibility": "accessibility.yaml",
}


def template_keys() -> list[str]:
    return sorted(_TEMPLATE_MAP.keys())


def template_filename(key: str) -> str | None:
    return _TEMPLATE_MAP.get(key)
