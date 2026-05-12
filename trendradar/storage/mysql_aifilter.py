# coding=utf-8
"""MySQL：AI 筛选相关表读写"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from pymysql.err import IntegrityError as MySQLIntegrityError

from trendradar.storage.mysql_news import _ensure_mysql_news_snippet_column

if TYPE_CHECKING:
    from trendradar.storage.mysql_mixin import MySQLStorageMixin


def get_active_tags_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> List[Dict[str, Any]]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            SELECT id, tag, description, version, prompt_hash, priority
            FROM ai_filter_tags
            WHERE day_key = %s AND status = 'active' AND interests_file = %s
            ORDER BY priority ASC, id ASC
            """,
            (dk, interests_file),
        )
        return [
            {
                "id": row[0],
                "tag": row[1],
                "description": row[2],
                "version": row[3],
                "prompt_hash": row[4],
                "priority": row[5],
            }
            for row in cursor.fetchall()
        ]
    except Exception as e:
        print(f"[AI筛选] 获取标签失败: {e}")
        return []


def get_latest_prompt_hash_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> Optional[str]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            SELECT prompt_hash FROM ai_filter_tags
            WHERE day_key = %s AND status = 'active' AND interests_file = %s
            ORDER BY version DESC
            LIMIT 1
            """,
            (dk, interests_file),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"[AI筛选] 获取 prompt_hash 失败: {e}")
        return None


def get_latest_tag_version_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            "SELECT MAX(version) FROM ai_filter_tags WHERE day_key = %s",
            (dk,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception as e:
        print(f"[AI筛选] 获取版本号失败: {e}")
        return 0


def deprecate_all_tags_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "SELECT id FROM ai_filter_tags WHERE day_key = %s AND status = 'active' AND interests_file = %s",
            (dk, interests_file),
        )
        tag_ids = [int(row[0]) for row in cursor.fetchall()]
        if not tag_ids:
            return 0

        ph = ",".join(["%s"] * len(tag_ids))
        cursor.execute(
            f"""
            UPDATE ai_filter_tags
            SET status = 'deprecated', deprecated_at = %s
            WHERE day_key = %s AND id IN ({ph})
            """,
            [now_str, dk] + tag_ids,
        )
        tag_count = cursor.rowcount

        cursor.execute(
            f"""
            UPDATE ai_filter_results
            SET status = 'deprecated', deprecated_at = %s
            WHERE day_key = %s AND tag_id IN ({ph}) AND status = 'active'
            """,
            [now_str, dk] + tag_ids,
        )

        conn.commit()
        print(f"[AI筛选] 已废弃 {tag_count} 个标签及关联分类结果")
        return tag_count
    except Exception as e:
        print(f"[AI筛选] 废弃标签失败: {e}")
        return 0


def save_tags_impl(
    mix: "MySQLStorageMixin",
    date: Optional[str],
    tags: List[Dict],
    version: int,
    prompt_hash: str,
    interests_file: str = "ai_interests.txt",
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

        count = 0
        for idx, tag_data in enumerate(tags, start=1):
            priority = tag_data.get("priority", idx)
            try:
                priority = int(priority)
            except (TypeError, ValueError):
                priority = idx
            cursor.execute(
                """
                INSERT INTO ai_filter_tags
                (day_key, tag, description, priority, version, prompt_hash, interests_file, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    dk,
                    tag_data["tag"],
                    tag_data.get("description", ""),
                    priority,
                    version,
                    prompt_hash,
                    interests_file,
                    now_str,
                ),
            )
            count += 1

        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 保存标签失败: {e}")
        return 0


def deprecate_specific_tags_impl(mix: "MySQLStorageMixin", date: Optional[str], tag_ids: List[int]) -> int:
    if not tag_ids:
        return 0
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
        ph = ",".join(["%s"] * len(tag_ids))

        cursor.execute(
            f"""
            UPDATE ai_filter_tags
            SET status = 'deprecated', deprecated_at = %s
            WHERE day_key = %s AND id IN ({ph})
            """,
            [now_str, dk] + tag_ids,
        )
        tag_count = cursor.rowcount

        cursor.execute(
            f"""
            UPDATE ai_filter_results
            SET status = 'deprecated', deprecated_at = %s
            WHERE day_key = %s AND tag_id IN ({ph}) AND status = 'active'
            """,
            [now_str, dk] + tag_ids,
        )

        conn.commit()
        return tag_count
    except Exception as e:
        print(f"[AI筛选] 废弃指定标签失败: {e}")
        return 0


def update_tags_hash_impl(mix: "MySQLStorageMixin", date: Optional[str], interests_file: str, new_hash: str) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            UPDATE ai_filter_tags
            SET prompt_hash = %s
            WHERE day_key = %s AND interests_file = %s AND status = 'active'
            """,
            (new_hash, dk, interests_file),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 更新标签 hash 失败: {e}")
        return 0


def update_tag_descriptions_impl(
    mix: "MySQLStorageMixin",
    date: Optional[str],
    tag_updates: List[Dict],
    interests_file: str = "ai_interests.txt",
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        count = 0
        for t in tag_updates:
            tag_name = t.get("tag", "")
            description = t.get("description", "")
            if not tag_name:
                continue
            cursor.execute(
                """
                UPDATE ai_filter_tags
                SET description = %s
                WHERE day_key = %s AND tag = %s AND interests_file = %s AND status = 'active'
                """,
                (description, dk, tag_name, interests_file),
            )
            count += cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 更新标签描述失败: {e}")
        return 0


def update_tag_priorities_impl(
    mix: "MySQLStorageMixin",
    date: Optional[str],
    tag_priorities: List[Dict],
    interests_file: str = "ai_interests.txt",
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        count = 0
        for t in tag_priorities:
            tag_name = t.get("tag", "")
            priority = t.get("priority")
            if not tag_name:
                continue
            try:
                priority = int(priority)
            except (TypeError, ValueError):
                continue
            cursor.execute(
                """
                UPDATE ai_filter_tags
                SET priority = %s
                WHERE day_key = %s AND tag = %s AND interests_file = %s AND status = 'active'
                """,
                (priority, dk, tag_name, interests_file),
            )
            count += cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 更新标签优先级失败: {e}")
        return 0


def save_analyzed_news_impl(
    mix: "MySQLStorageMixin",
    date: Optional[str],
    news_ids: List[int],
    source_type: str,
    interests_file: str,
    prompt_hash: str,
    matched_ids: Set[int],
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

        count = 0
        for nid in news_ids:
            try:
                cursor.execute(
                    """
                    INSERT INTO ai_filter_analyzed_news
                    (day_key, news_item_id, source_type, interests_file, prompt_hash, matched, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        prompt_hash = VALUES(prompt_hash),
                        matched = VALUES(matched),
                        created_at = VALUES(created_at)
                    """,
                    (
                        dk,
                        nid,
                        source_type,
                        interests_file,
                        prompt_hash,
                        1 if nid in matched_ids else 0,
                        now_str,
                    ),
                )
                count += 1
            except Exception:
                pass

        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 保存已分析记录失败: {e}")
        return 0


def get_analyzed_news_ids_impl(
    mix: "MySQLStorageMixin",
    date: Optional[str] = None,
    source_type: str = "hotlist",
    interests_file: str = "ai_interests.txt",
) -> Set[int]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            SELECT news_item_id FROM ai_filter_analyzed_news
            WHERE day_key = %s AND source_type = %s AND interests_file = %s
            """,
            (dk, source_type, interests_file),
        )
        return {int(row[0]) for row in cursor.fetchall()}
    except Exception as e:
        print(f"[AI筛选] 获取已分析ID失败: {e}")
        return set()


def clear_analyzed_news_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            "DELETE FROM ai_filter_analyzed_news WHERE day_key = %s AND interests_file = %s",
            (dk, interests_file),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 清除已分析记录失败: {e}")
        return 0


def clear_unmatched_analyzed_news_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            DELETE FROM ai_filter_analyzed_news
            WHERE day_key = %s AND interests_file = %s AND matched = 0
            """,
            (dk, interests_file),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 清除不匹配记录失败: {e}")
        return 0


def save_filter_results_impl(mix: "MySQLStorageMixin", date: Optional[str], results: List[Dict]) -> int:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

        count = 0
        for r in results:
            try:
                cursor.execute(
                    """
                    INSERT INTO ai_filter_results
                    (day_key, news_item_id, source_type, tag_id, relevance_score, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        dk,
                        r["news_item_id"],
                        r.get("source_type", "hotlist"),
                        r["tag_id"],
                        r.get("relevance_score", 0.0),
                        now_str,
                    ),
                )
                count += 1
            except MySQLIntegrityError:
                pass

        conn.commit()
        return count
    except Exception as e:
        print(f"[AI筛选] 保存分类结果失败: {e}")
        return 0


def get_active_filter_results_impl(
    mix: "MySQLStorageMixin", date: Optional[str] = None, interests_file: str = "ai_interests.txt"
) -> List[Dict[str, Any]]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)

        cursor.execute(
            """
            SELECT
                r.news_item_id, r.source_type, r.tag_id, r.relevance_score,
                t.tag, t.description as tag_description, t.priority,
                n.title, n.platform_id as source_id, p.name as source_name,
                n.url, n.mobile_url, n.`rank`,
                n.first_crawl_time, n.last_crawl_time, n.crawl_count
            FROM ai_filter_results r
            JOIN ai_filter_tags t ON r.tag_id = t.id AND r.day_key = t.day_key
            JOIN news_items n ON r.news_item_id = n.id AND r.day_key = n.day_key
            LEFT JOIN platforms p ON n.day_key = p.day_key AND n.platform_id = p.id
            WHERE r.day_key = %s AND r.status = 'active' AND r.source_type = 'hotlist'
                AND t.status = 'active' AND t.interests_file = %s
            ORDER BY t.priority ASC, t.id ASC, r.relevance_score DESC
            """,
            (dk, interests_file),
        )

        results: List[Dict[str, Any]] = []
        hotlist_news_ids: List[int] = []
        for row in cursor.fetchall():
            results.append(
                {
                    "news_item_id": row[0],
                    "source_type": row[1],
                    "tag_id": row[2],
                    "relevance_score": row[3],
                    "tag": row[4],
                    "tag_description": row[5],
                    "tag_priority": row[6],
                    "title": row[7],
                    "source_id": row[8],
                    "source_name": row[9] or row[8],
                    "url": row[10] or "",
                    "mobile_url": row[11] or "",
                    "rank": row[12],
                    "first_time": row[13],
                    "last_time": row[14],
                    "count": row[15],
                }
            )
            hotlist_news_ids.append(int(row[0]))

        ranks_map: Dict[int, List[int]] = {}
        if hotlist_news_ids:
            unique_ids = list(set(hotlist_news_ids))
            ph = ",".join(["%s"] * len(unique_ids))
            cursor.execute(
                f"""
                SELECT news_item_id, `rank` FROM rank_history
                WHERE day_key = %s AND news_item_id IN ({ph}) AND `rank` != 0
                """,
                (dk, *unique_ids),
            )
            for rh_row in cursor.fetchall():
                nid, rank = int(rh_row[0]), rh_row[1]
                if nid not in ranks_map:
                    ranks_map[nid] = []
                if rank not in ranks_map[nid]:
                    ranks_map[nid].append(rank)

        for item in results:
            item["ranks"] = ranks_map.get(item["news_item_id"], [item["rank"]])

        try:
            rss_conn = mix._get_connection(date, db_type="rss")
            rss_cursor = rss_conn.cursor()

            cursor.execute(
                """
                SELECT r.news_item_id, r.tag_id, r.relevance_score,
                       t.tag, t.description, t.priority
                FROM ai_filter_results r
                JOIN ai_filter_tags t ON r.tag_id = t.id AND r.day_key = t.day_key
                WHERE r.day_key = %s AND r.status = 'active' AND r.source_type = 'rss'
                    AND t.status = 'active' AND t.interests_file = %s
                ORDER BY t.priority ASC, t.id ASC, r.relevance_score DESC
                """,
                (dk, interests_file),
            )
            rss_filter_rows = cursor.fetchall()
            if rss_filter_rows:
                rss_ids = [int(row[0]) for row in rss_filter_rows]
                ph = ",".join(["%s"] * len(rss_ids))
                rss_cursor.execute(
                    f"""
                    SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                           i.url, i.published_at
                    FROM rss_items i
                    LEFT JOIN rss_feeds f ON i.day_key = f.day_key AND i.feed_id = f.id
                    WHERE i.day_key = %s AND i.id IN ({ph})
                    """,
                    (dk, *rss_ids),
                )
                rss_info = {int(row[0]): row for row in rss_cursor.fetchall()}

                for fr_row in rss_filter_rows:
                    rss_id = int(fr_row[0])
                    info = rss_info.get(rss_id)
                    if info:
                        results.append(
                            {
                                "news_item_id": rss_id,
                                "source_type": "rss",
                                "tag_id": fr_row[1],
                                "relevance_score": fr_row[2],
                                "tag": fr_row[3],
                                "tag_description": fr_row[4],
                                "tag_priority": fr_row[5],
                                "title": info[1],
                                "source_id": info[2],
                                "source_name": info[3] or info[2],
                                "url": info[4] or "",
                                "mobile_url": "",
                                "rank": 0,
                                "ranks": [],
                                "first_time": info[5] or "",
                                "last_time": info[5] or "",
                                "count": 1,
                            }
                        )
        except Exception:
            pass

        return results
    except Exception as e:
        print(f"[AI筛选] 获取分类结果失败: {e}")
        return []


def get_all_news_ids_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> List[Dict]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        _ensure_mysql_news_snippet_column(cursor)
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            SELECT n.id, n.title, n.platform_id, p.name as platform_name,
                   COALESCE(n.snippet, '')
            FROM news_items n
            LEFT JOIN platforms p ON n.day_key = p.day_key AND n.platform_id = p.id
            WHERE n.day_key = %s
            ORDER BY n.id
            """,
            (dk,),
        )
        return [
            {
                "id": int(row[0]),
                "title": row[1],
                "source_id": row[2],
                "source_name": row[3] or row[2],
                "snippet": row[4] or "",
            }
            for row in cursor.fetchall()
        ]
    except Exception as e:
        print(f"[AI筛选] 获取新闻列表失败: {e}")
        return []


def get_all_rss_ids_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> List[Dict]:
    try:
        conn = mix._get_connection(date, db_type="rss")
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            """
            SELECT i.id, i.title, i.feed_id, f.name as feed_name, i.published_at,
                   COALESCE(i.summary, '')
            FROM rss_items i
            LEFT JOIN rss_feeds f ON i.day_key = f.day_key AND i.feed_id = f.id
            WHERE i.day_key = %s
            ORDER BY i.id
            """,
            (dk,),
        )
        return [
            {
                "id": int(row[0]),
                "title": row[1],
                "source_id": row[2],
                "source_name": row[3] or row[2],
                "published_at": row[4] or "",
                "summary": row[5] or "",
            }
            for row in cursor.fetchall()
        ]
    except Exception as e:
        print(f"[AI筛选] 获取 RSS 列表失败: {e}")
        return []
