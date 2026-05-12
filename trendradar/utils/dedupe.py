# coding=utf-8
"""跨平台选题去重：规范化标题与 URL 辅助键。"""

import re
import unicodedata

from trendradar.utils.url import normalize_url


def canonical_title_key(title: str) -> str:
    """
    将标题转为可比较的规范化键（用于无 URL 时的弱去重）。
    不保证语义等价，仅降低「标点/空白差异」导致的重复。
    """
    if not title or not isinstance(title, str):
        return ""
    t = unicodedata.normalize("NFKC", title)
    t = t.lower().strip()
    t = re.sub(r"[\s\u200b\u3000]+", "", t)
    t = re.sub(r"[^\w\u4e00-\u9fff]", "", t)
    return t


def normalized_news_url(url: str, platform_id: str) -> str:
    """热榜条目 URL 标准化（与存储层一致）。"""
    if not url or not isinstance(url, str):
        return ""
    return normalize_url(url.strip(), platform_id) or ""


def should_skip_cross_platform(
    url: str,
    platform_id: str,
    title: str,
    seen_urls: set,
    seen_titles_no_url: set,
    *,
    by_url: bool = True,
    by_title_if_no_url: bool = True,
) -> bool:
    """
    若应跳过当前条目（与先前平台已出现的同题重复），返回 True，并更新 seen 集合。
    策略：有标准化 URL 时以 URL 为准；否则可选地用规范化标题。
    """
    nu = normalized_news_url(url, platform_id) if by_url else ""
    if nu:
        if nu in seen_urls:
            return True
        seen_urls.add(nu)
        return False

    if not by_title_if_no_url:
        return False

    ck = canonical_title_key(title)
    if not ck or len(ck) < 6:
        return False

    if ck in seen_titles_no_url:
        return True
    seen_titles_no_url.add(ck)
    return False
