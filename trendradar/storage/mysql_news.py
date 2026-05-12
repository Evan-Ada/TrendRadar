# coding=utf-8
"""MySQL：热榜 news 相关读写（按 day_key 隔离，对应原按日 SQLite 文件）"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pymysql.err import Error as MySQLError

from trendradar.storage.base import NewsData, NewsItem
from trendradar.utils.url import normalize_url

if TYPE_CHECKING:
    from trendradar.storage.mysql_mixin import MySQLStorageMixin


def _ensure_mysql_news_snippet_column(cursor) -> None:
    try:
        cursor.execute(
            "ALTER TABLE news_items ADD COLUMN snippet TEXT NULL COMMENT 'OG/描述补全'"
        )
    except MySQLError:
        pass


def save_news_data_impl(mix: "MySQLStorageMixin", data: NewsData, log_prefix: str = "[存储]") -> tuple[bool, int, int, int, int]:
    try:
        conn = mix._get_connection(data.date)
        cursor = conn.cursor()
        _ensure_mysql_news_snippet_column(cursor)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
        dk = mix._format_date_folder(data.date)

        for source_id, source_name in data.id_to_name.items():
            cursor.execute(
                """
                INSERT INTO platforms (day_key, id, name, updated_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = VALUES(updated_at)
                """,
                (dk, source_id, source_name, now_str),
            )

        new_count = 0
        updated_count = 0
        title_changed_count = 0
        success_sources: List[str] = []

        for source_id, news_list in data.items.items():
            success_sources.append(source_id)
            for item in news_list:
                try:
                    snippet_val = getattr(item, "snippet", "") or ""
                    normalized_url = normalize_url(item.url, source_id) if item.url else None
                    url_val = normalized_url if normalized_url else None

                    if normalized_url:
                        cursor.execute(
                            """
                            SELECT id, title FROM news_items
                            WHERE day_key = %s AND url <=> %s AND platform_id = %s
                            """,
                            (dk, url_val, source_id),
                        )
                        existing = cursor.fetchone()

                        if existing:
                            existing_id, existing_title = existing

                            if existing_title != item.title:
                                cursor.execute(
                                    """
                                    INSERT INTO title_changes
                                    (day_key, news_item_id, old_title, new_title, changed_at)
                                    VALUES (%s, %s, %s, %s, %s)
                                    """,
                                    (dk, existing_id, existing_title, item.title, now_str),
                                )
                                title_changed_count += 1

                            cursor.execute(
                                """
                                INSERT INTO rank_history
                                (day_key, news_item_id, `rank`, crawl_time, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (dk, existing_id, item.rank, data.crawl_time, now_str),
                            )

                            cursor.execute(
                                """
                                UPDATE news_items SET
                                    title = %s,
                                    `rank` = %s,
                                    mobile_url = %s,
                                    last_crawl_time = %s,
                                    crawl_count = crawl_count + 1,
                                    updated_at = %s,
                                    snippet = COALESCE(NULLIF(TRIM(%s), ''), snippet)
                                WHERE id = %s AND day_key = %s
                                """,
                                (
                                    item.title,
                                    item.rank,
                                    item.mobile_url,
                                    data.crawl_time,
                                    now_str,
                                    snippet_val,
                                    existing_id,
                                    dk,
                                ),
                            )
                            updated_count += 1
                        else:
                            cursor.execute(
                                """
                                INSERT INTO news_items
                                (day_key, title, platform_id, `rank`, url, mobile_url, snippet,
                                 first_crawl_time, last_crawl_time, crawl_count,
                                 created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                                """,
                                (
                                    dk,
                                    item.title,
                                    source_id,
                                    item.rank,
                                    url_val,
                                    item.mobile_url,
                                    snippet_val,
                                    data.crawl_time,
                                    data.crawl_time,
                                    now_str,
                                    now_str,
                                ),
                            )
                            new_id = int(cursor.lastrowid)
                            cursor.execute(
                                """
                                INSERT INTO rank_history
                                (day_key, news_item_id, `rank`, crawl_time, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (dk, new_id, item.rank, data.crawl_time, now_str),
                            )
                            new_count += 1
                    else:
                        cursor.execute(
                            """
                            INSERT INTO news_items
                            (day_key, title, platform_id, `rank`, url, mobile_url, snippet,
                             first_crawl_time, last_crawl_time, crawl_count,
                             created_at, updated_at)
                            VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, 1, %s, %s)
                            """,
                            (
                                dk,
                                item.title,
                                source_id,
                                item.rank,
                                item.mobile_url,
                                snippet_val,
                                data.crawl_time,
                                data.crawl_time,
                                now_str,
                                now_str,
                            ),
                        )
                        new_id = int(cursor.lastrowid)
                        cursor.execute(
                            """
                            INSERT INTO rank_history
                            (day_key, news_item_id, `rank`, crawl_time, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (dk, new_id, item.rank, data.crawl_time, now_str),
                        )
                        new_count += 1

                except MySQLError as e:
                    print(f"{log_prefix} 保存新闻条目失败 [{item.title[:30]}...]: {e}")

        total_items = new_count + updated_count
        off_list_count = 0

        cursor.execute(
            """
            SELECT crawl_time FROM crawl_records
            WHERE day_key = %s AND crawl_time < %s
            ORDER BY crawl_time DESC
            LIMIT 1
            """,
            (dk, data.crawl_time),
        )
        prev_record = cursor.fetchone()

        if prev_record:
            prev_crawl_time = prev_record[0]
            for source_id in success_sources:
                current_urls = set()
                for item in data.items.get(source_id, []):
                    nu = normalize_url(item.url, source_id) if item.url else None
                    if nu:
                        current_urls.add(nu)

                cursor.execute(
                    """
                    SELECT id, url FROM news_items
                    WHERE day_key = %s AND platform_id = %s
                      AND last_crawl_time = %s
                      AND url IS NOT NULL AND url != ''
                    """,
                    (dk, source_id, prev_crawl_time),
                )
                for row in cursor.fetchall():
                    news_id, url = row[0], row[1]
                    if url not in current_urls:
                        cursor.execute(
                            """
                            INSERT INTO rank_history
                            (day_key, news_item_id, `rank`, crawl_time, created_at)
                            VALUES (%s, %s, 0, %s, %s)
                            """,
                            (dk, news_id, data.crawl_time, now_str),
                        )
                        off_list_count += 1

        cursor.execute(
            """
            INSERT INTO crawl_records (day_key, crawl_time, total_items, created_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE total_items = VALUES(total_items), created_at = VALUES(created_at)
            """,
            (dk, data.crawl_time, total_items, now_str),
        )

        cursor.execute(
            "SELECT id FROM crawl_records WHERE day_key = %s AND crawl_time = %s",
            (dk, data.crawl_time),
        )
        record_row = cursor.fetchone()
        if record_row:
            crawl_record_id = int(record_row[0])
            for source_id in success_sources:
                cursor.execute(
                    """
                    INSERT INTO crawl_source_status (day_key, crawl_record_id, platform_id, status)
                    VALUES (%s, %s, %s, 'success')
                    ON DUPLICATE KEY UPDATE status = VALUES(status), day_key = VALUES(day_key)
                    """,
                    (dk, crawl_record_id, source_id),
                )

            for failed_id in data.failed_ids:
                cursor.execute(
                    """
                    INSERT IGNORE INTO platforms (day_key, id, name, updated_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (dk, failed_id, failed_id, now_str),
                )
                cursor.execute(
                    """
                    INSERT INTO crawl_source_status (day_key, crawl_record_id, platform_id, status)
                    VALUES (%s, %s, %s, 'failed')
                    ON DUPLICATE KEY UPDATE status = VALUES(status), day_key = VALUES(day_key)
                    """,
                    (dk, crawl_record_id, failed_id),
                )

        conn.commit()
        return True, new_count, updated_count, title_changed_count, off_list_count

    except Exception as e:
        print(f"{log_prefix} 保存失败: {e}")
        return False, 0, 0, 0, 0


def get_today_all_data_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> Optional[NewsData]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        _ensure_mysql_news_snippet_column(cursor)
        dk = mix._format_date_folder(date)

        cursor.execute(
            """
            SELECT n.id, n.title, n.platform_id, p.name as platform_name,
                   n.`rank`, n.url, n.mobile_url, COALESCE(n.snippet, ''),
                   n.first_crawl_time, n.last_crawl_time, n.crawl_count
            FROM news_items n
            LEFT JOIN platforms p ON n.day_key = p.day_key AND n.platform_id = p.id
            WHERE n.day_key = %s
            ORDER BY n.platform_id, n.last_crawl_time
            """,
            (dk,),
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        news_ids = [int(row[0]) for row in rows]
        rank_history_map: Dict[int, List[int]] = {}
        rank_timeline_map: Dict[int, List[Dict[str, Any]]] = {}
        if news_ids:
            ph = ",".join(["%s"] * len(news_ids))
            cursor.execute(
                f"""
                SELECT rh.news_item_id, rh.`rank`, rh.crawl_time
                FROM rank_history rh
                JOIN news_items ni ON rh.news_item_id = ni.id AND rh.day_key = ni.day_key
                WHERE rh.day_key = %s AND rh.news_item_id IN ({ph})
                  AND NOT (rh.rank = 0 AND rh.crawl_time > ni.last_crawl_time)
                ORDER BY rh.news_item_id, rh.crawl_time
                """,
                (dk, *news_ids),
            )
            for rh_row in cursor.fetchall():
                news_id, rank, crawl_time = int(rh_row[0]), rh_row[1], rh_row[2]
                if news_id not in rank_history_map:
                    rank_history_map[news_id] = []
                if rank != 0 and rank not in rank_history_map[news_id]:
                    rank_history_map[news_id].append(rank)
                if news_id not in rank_timeline_map:
                    rank_timeline_map[news_id] = []
                ct = str(crawl_time)
                time_part = ct.split()[1][:5] if " " in ct else ct[:5]
                rank_timeline_map[news_id].append({"time": time_part, "rank": rank if rank != 0 else None})

        items: Dict[str, List[NewsItem]] = {}
        id_to_name: Dict[str, str] = {}
        crawl_date = dk

        for row in rows:
            news_id = int(row[0])
            platform_id = row[2]
            title = row[1]
            platform_name = row[3] or platform_id
            id_to_name[platform_id] = platform_name
            if platform_id not in items:
                items[platform_id] = []
            ranks = rank_history_map.get(news_id, [row[4]])
            rank_timeline = rank_timeline_map.get(news_id, [])
            u = row[5]
            items[platform_id].append(
                NewsItem(
                    title=title,
                    source_id=platform_id,
                    source_name=platform_name,
                    rank=row[4],
                    url=u if u is not None else "",
                    mobile_url=row[6] or "",
                    snippet=row[7] or "",
                    crawl_time=row[9],
                    ranks=ranks,
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                    rank_timeline=rank_timeline,
                )
            )

        cursor.execute(
            """
            SELECT DISTINCT css.platform_id
            FROM crawl_source_status css
            JOIN crawl_records cr ON css.crawl_record_id = cr.id
            WHERE css.day_key = %s AND cr.day_key = %s AND css.status = 'failed'
            """,
            (dk, dk),
        )
        failed_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT crawl_time FROM crawl_records
            WHERE day_key = %s
            ORDER BY crawl_time DESC
            LIMIT 1
            """,
            (dk,),
        )
        time_row = cursor.fetchone()
        crawl_time = time_row[0] if time_row else mix._format_time_filename()

        return NewsData(
            date=crawl_date,
            crawl_time=crawl_time,
            items=items,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
        )
    except Exception as e:
        print(f"[存储] 读取数据失败: {e}")
        return None


def get_latest_crawl_data_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> Optional[NewsData]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        _ensure_mysql_news_snippet_column(cursor)
        dk = mix._format_date_folder(date)

        cursor.execute(
            """
            SELECT crawl_time FROM crawl_records
            WHERE day_key = %s
            ORDER BY crawl_time DESC
            LIMIT 1
            """,
            (dk,),
        )
        time_row = cursor.fetchone()
        if not time_row:
            return None
        latest_time = time_row[0]

        cursor.execute(
            """
            SELECT n.id, n.title, n.platform_id, p.name as platform_name,
                   n.`rank`, n.url, n.mobile_url, COALESCE(n.snippet, ''),
                   n.first_crawl_time, n.last_crawl_time, n.crawl_count
            FROM news_items n
            LEFT JOIN platforms p ON n.day_key = p.day_key AND n.platform_id = p.id
            WHERE n.day_key = %s AND n.last_crawl_time = %s
            """,
            (dk, latest_time),
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        news_ids = [int(row[0]) for row in rows]
        rank_history_map: Dict[int, List[int]] = {}
        rank_timeline_map: Dict[int, List[Dict[str, Any]]] = {}
        if news_ids:
            ph = ",".join(["%s"] * len(news_ids))
            cursor.execute(
                f"""
                SELECT rh.news_item_id, rh.`rank`, rh.crawl_time
                FROM rank_history rh
                JOIN news_items ni ON rh.news_item_id = ni.id AND rh.day_key = ni.day_key
                WHERE rh.day_key = %s AND rh.news_item_id IN ({ph})
                  AND NOT (rh.rank = 0 AND rh.crawl_time > ni.last_crawl_time)
                ORDER BY rh.news_item_id, rh.crawl_time
                """,
                (dk, *news_ids),
            )
            for rh_row in cursor.fetchall():
                news_id, rank, crawl_time = int(rh_row[0]), rh_row[1], rh_row[2]
                if news_id not in rank_history_map:
                    rank_history_map[news_id] = []
                if rank != 0 and rank not in rank_history_map[news_id]:
                    rank_history_map[news_id].append(rank)
                if news_id not in rank_timeline_map:
                    rank_timeline_map[news_id] = []
                ct = str(crawl_time)
                time_part = ct.split()[1][:5] if " " in ct else ct[:5]
                rank_timeline_map[news_id].append({"time": time_part, "rank": rank if rank != 0 else None})

        items: Dict[str, List[NewsItem]] = {}
        id_to_name: Dict[str, str] = {}
        crawl_date = dk

        for row in rows:
            news_id = int(row[0])
            platform_id = row[2]
            platform_name = row[3] or platform_id
            id_to_name[platform_id] = platform_name
            if platform_id not in items:
                items[platform_id] = []
            ranks = rank_history_map.get(news_id, [row[4]])
            rank_timeline = rank_timeline_map.get(news_id, [])
            u = row[5]
            items[platform_id].append(
                NewsItem(
                    title=row[1],
                    source_id=platform_id,
                    source_name=platform_name,
                    rank=row[4],
                    url=u if u is not None else "",
                    mobile_url=row[6] or "",
                    snippet=row[7] or "",
                    crawl_time=row[9],
                    ranks=ranks,
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                    rank_timeline=rank_timeline,
                )
            )

        cursor.execute(
            """
            SELECT css.platform_id
            FROM crawl_source_status css
            JOIN crawl_records cr ON css.crawl_record_id = cr.id
            WHERE css.day_key = %s AND cr.day_key = %s
              AND cr.crawl_time = %s AND css.status = 'failed'
            """,
            (dk, dk, latest_time),
        )
        failed_ids = [row[0] for row in cursor.fetchall()]

        return NewsData(
            date=crawl_date,
            crawl_time=latest_time,
            items=items,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
        )
    except Exception as e:
        print(f"[存储] 获取最新数据失败: {e}")
        return None


def detect_new_titles_impl(mix: "MySQLStorageMixin", current_data: NewsData) -> Dict[str, Dict]:
    try:
        historical_data = get_today_all_data_impl(mix, current_data.date)
        if not historical_data:
            return {sid: {it.title: it for it in lst} for sid, lst in current_data.items.items()}

        current_time = current_data.crawl_time
        historical_titles: Dict[str, set] = {}
        for source_id, news_list in historical_data.items.items():
            historical_titles[source_id] = set()
            for item in news_list:
                first_time = item.first_time or item.crawl_time
                if first_time < current_time:
                    historical_titles[source_id].add(item.title)

        if not any(len(titles) > 0 for titles in historical_titles.values()):
            return {}

        new_titles: Dict[str, Dict] = {}
        for source_id, news_list in current_data.items.items():
            hist_set = historical_titles.get(source_id, set())
            for item in news_list:
                if item.title not in hist_set:
                    if source_id not in new_titles:
                        new_titles[source_id] = {}
                    new_titles[source_id][item.title] = item
        return new_titles
    except Exception as e:
        print(f"[存储] 检测新标题失败: {e}")
        return {}


def is_first_crawl_today_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> bool:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            "SELECT COUNT(*) FROM crawl_records WHERE day_key = %s",
            (dk,),
        )
        row = cursor.fetchone()
        count = int(row[0]) if row else 0
        return count <= 1
    except Exception as e:
        print(f"[存储] 检查首次抓取失败: {e}")
        return True


def get_crawl_times_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> List[str]:
    try:
        conn = mix._get_connection(date)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)
        cursor.execute(
            "SELECT crawl_time FROM crawl_records WHERE day_key = %s ORDER BY crawl_time",
            (dk,),
        )
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[存储] 获取抓取时间列表失败: {e}")
        return []


def has_period_executed_impl(mix: "MySQLStorageMixin", date_str: str, period_key: str, action: str) -> bool:
    try:
        conn = mix._get_connection(date_str)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date_str)
        cursor.execute(
            """
            SELECT 1 FROM period_executions
            WHERE day_key = %s AND execution_date = %s AND period_key = %s AND action = %s
            LIMIT 1
            """,
            (dk, date_str, period_key, action),
        )
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"[存储] 检查时间段执行记录失败: {e}")
        return False


def record_period_execution_impl(mix: "MySQLStorageMixin", date_str: str, period_key: str, action: str) -> bool:
    try:
        conn = mix._get_connection(date_str)
        cursor = conn.cursor()
        dk = mix._format_date_folder(date_str)
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT IGNORE INTO period_executions
            (day_key, execution_date, period_key, action, executed_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (dk, date_str, period_key, action, now_str),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[存储] 记录时间段执行失败: {e}")
        return False
