# coding=utf-8
"""
从详情页 HTML 提取简短描述（og:description / meta description），用于热榜条目 snippet。
"""

from __future__ import annotations

import html as html_module
import re
import time
from typing import Optional

import requests

# 单次响应最多读取字节数，防止异常大页面
_MAX_RESPONSE_BYTES = 600_000

_OG_DESC_RE = re.compile(
    r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_OG_DESC_RE2 = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*property=["\']og:description["\']',
    re.IGNORECASE,
)
_META_NAME_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_META_NAME_DESC_RE2 = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
    re.IGNORECASE,
)


def _clean_snippet(raw: str, max_length: int) -> str:
    if not raw:
        return ""
    t = html_module.unescape(raw).strip()
    t = re.sub(r"\s+", " ", t)
    if max_length > 0 and len(t) > max_length:
        t = t[: max_length - 1].rstrip() + "…"
    return t


def _first_match(patterns: list[re.Pattern], text: str) -> Optional[str]:
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def fetch_page_snippet(
    url: str,
    *,
    timeout: float = 10.0,
    max_length: int = 450,
) -> str:
    """
    GET 指定 URL，从 HTML 头部元信息提取描述性文本。
    失败或无可提取内容时返回空字符串。
    """
    if not url or not isinstance(url, str):
        return ""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "TrendRadar/2.0 SnippetFetcher (compatible; +https://github.com/trendradar)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    )

    try:
        resp = session.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total >= _MAX_RESPONSE_BYTES:
                break
        raw_bytes = b"".join(chunks)
        text = raw_bytes.decode(resp.encoding or "utf-8", errors="replace")
    except requests.RequestException:
        return ""
    finally:
        session.close()

    head = text[: min(len(text), 400_000)]
    raw = _first_match([_OG_DESC_RE, _OG_DESC_RE2, _META_NAME_DESC_RE, _META_NAME_DESC_RE2], head)
    if not raw:
        return ""
    return _clean_snippet(raw, max_length)


def enrich_hotlist_results_snippets(
    results: dict,
    *,
    top_n_per_platform: int = 8,
    max_length: int = 450,
    timeout_seconds: float = 10.0,
    request_interval_ms: int = 280,
) -> int:
    """
    就地写入 results[platform_id][title]['snippet']。
    每个平台仅处理排名前 top_n_per_platform 的条目（按最小 rank 排序）。

    Returns:
        成功写入非空 snippet 的条数。
    """
    if top_n_per_platform <= 0:
        return 0

    filled = 0
    interval_s = max(0, request_interval_ms) / 1000.0

    for _platform_id, titles_data in results.items():
        if not titles_data:
            continue

        def sort_key(item: tuple) -> tuple:
            title, data = item
            ranks = data.get("ranks") or []
            return (min(ranks) if ranks else 999, title)

        items = sorted(titles_data.items(), key=sort_key)[:top_n_per_platform]

        for title, data in items:
            if data.get("snippet"):
                continue
            link = (data.get("url") or "").strip() or (data.get("mobileUrl") or "").strip()
            if not link:
                continue
            sn = fetch_page_snippet(link, timeout=timeout_seconds, max_length=max_length)
            if sn:
                data["snippet"] = sn
                filled += 1
            if interval_s > 0:
                time.sleep(interval_s)

    return filled
