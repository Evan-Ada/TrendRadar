# coding=utf-8
"""MySQL：RSS 读写"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from pymysql.err import Error as MySQLError
from pymysql.err import IntegrityError as MySQLIntegrityError

from trendradar.storage.base import RSSData, RSSItem

if TYPE_CHECKING:
    from trendradar.storage.mysql_mixin import MySQLStorageMixin


def save_rss_data_impl(mix: "MySQLStorageMixin", data: RSSData, log_prefix: str = "[存储]") -> tuple[bool, int, int]:
    try:
        conn = mix._get_connection(data.date, db_type="rss")
        cursor = conn.cursor()
        now_str = mix._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
        dk = mix._format_date_folder(data.date)

        for feed_id, feed_name in data.id_to_name.items():
            cursor.execute(
                """
                INSERT INTO rss_feeds (day_key, id, name, updated_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = VALUES(updated_at)
                """,
                (dk, feed_id, feed_name, now_str),
            )

        new_count = 0
        updated_count = 0

        for feed_id, rss_list in data.items.items():
            for item in rss_list:
                try:
                    if item.url:
                        cursor.execute(
                            """
                            SELECT id, title FROM rss_items
                            WHERE day_key = %s AND url = %s AND feed_id = %s
                            """,
                            (dk, item.url, feed_id),
                        )
                        existing = cursor.fetchone()

                        if existing:
                            existing_id = int(existing[0])
                            cursor.execute(
                                """
                                UPDATE rss_items SET
                                    title = %s,
                                    published_at = %s,
                                    summary = %s,
                                    author = %s,
                                    last_crawl_time = %s,
                                    crawl_count = crawl_count + 1,
                                    updated_at = %s
                                WHERE id = %s AND day_key = %s
                                """,
                                (
                                    item.title,
                                    item.published_at,
                                    item.summary,
                                    item.author,
                                    data.crawl_time,
                                    now_str,
                                    existing_id,
                                    dk,
                                ),
                            )
                            updated_count += 1
                        else:
                            cursor.execute(
                                """
                                INSERT INTO rss_items
                                (day_key, title, feed_id, url, published_at, summary, author,
                                 first_crawl_time, last_crawl_time, crawl_count,
                                 created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    title = VALUES(title),
                                    published_at = VALUES(published_at),
                                    summary = VALUES(summary),
                                    author = VALUES(author),
                                    last_crawl_time = VALUES(last_crawl_time),
                                    crawl_count = crawl_count + 1,
                                    updated_at = VALUES(updated_at)
                                """,
                                (
                                    dk,
                                    item.title,
                                    feed_id,
                                    item.url,
                                    item.published_at,
                                    item.summary,
                                    item.author,
                                    data.crawl_time,
                                    data.crawl_time,
                                    now_str,
                                    now_str,
                                ),
                            )
                            new_count += 1
                    else:
                        try:
                            cursor.execute(
                                """
                                INSERT INTO rss_items
                                (day_key, title, feed_id, url, published_at, summary, author,
                                 first_crawl_time, last_crawl_time, crawl_count,
                                 created_at, updated_at)
                                VALUES (%s, %s, %s, '', %s, %s, %s, %s, %s, 1, %s, %s)
                                """,
                                (
                                    dk,
                                    item.title,
                                    feed_id,
                                    item.published_at,
                                    item.summary,
                                    item.author,
                                    data.crawl_time,
                                    data.crawl_time,
                                    now_str,
                                    now_str,
                                ),
                            )
                            new_count += 1
                        except MySQLIntegrityError:
                            pass

                except MySQLError as e:
                    print(f"{log_prefix} 保存 RSS 条目失败 [{item.title[:30]}...]: {e}")

        total_items = new_count + updated_count

        cursor.execute(
            """
            INSERT INTO rss_crawl_records (day_key, crawl_time, total_items, created_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE total_items = VALUES(total_items), created_at = VALUES(created_at)
            """,
            (dk, data.crawl_time, total_items, now_str),
        )

        cursor.execute(
            "SELECT id FROM rss_crawl_records WHERE day_key = %s AND crawl_time = %s",
            (dk, data.crawl_time),
        )
        record_row = cursor.fetchone()
        if record_row:
            crawl_record_id = int(record_row[0])
            for feed_id in data.items.keys():
                cursor.execute(
                    """
                    INSERT INTO rss_crawl_status (day_key, crawl_record_id, feed_id, status)
                    VALUES (%s, %s, %s, 'success')
                    ON DUPLICATE KEY UPDATE status = VALUES(status), day_key = VALUES(day_key)
                    """,
                    (dk, crawl_record_id, feed_id),
                )

            for failed_id in data.failed_ids:
                cursor.execute(
                    """
                    INSERT IGNORE INTO rss_feeds (day_key, id, name, updated_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (dk, failed_id, failed_id, now_str),
                )
                cursor.execute(
                    """
                    INSERT INTO rss_crawl_status (day_key, crawl_record_id, feed_id, status)
                    VALUES (%s, %s, %s, 'failed')
                    ON DUPLICATE KEY UPDATE status = VALUES(status), day_key = VALUES(day_key)
                    """,
                    (dk, crawl_record_id, failed_id),
                )

        conn.commit()
        return True, new_count, updated_count

    except Exception as e:
        print(f"{log_prefix} 保存 RSS 数据失败: {e}")
        return False, 0, 0


def get_rss_data_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> Optional[RSSData]:
    try:
        conn = mix._get_connection(date, db_type="rss")
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)

        cursor.execute(
            """
            SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                   i.url, i.published_at, i.summary, i.author,
                   i.first_crawl_time, i.last_crawl_time, i.crawl_count
            FROM rss_items i
            LEFT JOIN rss_feeds f ON i.day_key = f.day_key AND i.feed_id = f.id
            WHERE i.day_key = %s
            ORDER BY i.published_at DESC
            """,
            (dk,),
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        items: Dict[str, List[RSSItem]] = {}
        id_to_name: Dict[str, str] = {}
        crawl_date = dk

        for row in rows:
            feed_id = row[2]
            feed_name = row[3] or feed_id
            id_to_name[feed_id] = feed_name
            if feed_id not in items:
                items[feed_id] = []
            items[feed_id].append(
                RSSItem(
                    title=row[1],
                    feed_id=feed_id,
                    feed_name=feed_name,
                    url=row[4] or "",
                    published_at=row[5] or "",
                    summary=row[6] or "",
                    author=row[7] or "",
                    crawl_time=row[9],
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                )
            )

        cursor.execute(
            """
            SELECT crawl_time FROM rss_crawl_records
            WHERE day_key = %s
            ORDER BY crawl_time DESC
            LIMIT 1
            """,
            (dk,),
        )
        time_row = cursor.fetchone()
        crawl_time = time_row[0] if time_row else mix._format_time_filename()

        cursor.execute(
            """
            SELECT DISTINCT cs.feed_id
            FROM rss_crawl_status cs
            JOIN rss_crawl_records cr ON cs.crawl_record_id = cr.id
            WHERE cs.day_key = %s AND cr.day_key = %s AND cs.status = 'failed'
            """,
            (dk, dk),
        )
        failed_ids = [row[0] for row in cursor.fetchall()]

        return RSSData(
            date=crawl_date,
            crawl_time=crawl_time,
            items=items,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
        )
    except Exception as e:
        print(f"[存储] 读取 RSS 数据失败: {e}")
        return None


def detect_new_rss_items_impl(mix: "MySQLStorageMixin", current_data: RSSData) -> Dict[str, List[RSSItem]]:
    try:
        historical_data = get_rss_data_impl(mix, current_data.date)
        if not historical_data:
            return current_data.items.copy()

        current_time = current_data.crawl_time
        historical_urls: Dict[str, set] = {}
        for feed_id, rss_list in historical_data.items.items():
            historical_urls[feed_id] = set()
            for item in rss_list:
                first_time = item.first_time or item.crawl_time
                if first_time < current_time and item.url:
                    historical_urls[feed_id].add(item.url)

        if not any(len(urls) > 0 for urls in historical_urls.values()):
            return {}

        new_items: Dict[str, List[RSSItem]] = {}
        for feed_id, rss_list in current_data.items.items():
            hist_set = historical_urls.get(feed_id, set())
            for item in rss_list:
                if item.url and item.url not in hist_set:
                    if feed_id not in new_items:
                        new_items[feed_id] = []
                    new_items[feed_id].append(item)
        return new_items
    except Exception as e:
        print(f"[存储] 检测新 RSS 条目失败: {e}")
        return {}


def get_latest_rss_data_impl(mix: "MySQLStorageMixin", date: Optional[str] = None) -> Optional[RSSData]:
    try:
        conn = mix._get_connection(date, db_type="rss")
        cursor = conn.cursor()
        dk = mix._format_date_folder(date)

        cursor.execute(
            """
            SELECT crawl_time FROM rss_crawl_records
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
            SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                   i.url, i.published_at, i.summary, i.author,
                   i.first_crawl_time, i.last_crawl_time, i.crawl_count
            FROM rss_items i
            LEFT JOIN rss_feeds f ON i.day_key = f.day_key AND i.feed_id = f.id
            WHERE i.day_key = %s AND i.last_crawl_time = %s
            ORDER BY i.published_at DESC
            """,
            (dk, latest_time),
        )
        rows = cursor.fetchall()
        if not rows:
            return None

        items: Dict[str, List[RSSItem]] = {}
        id_to_name: Dict[str, str] = {}
        crawl_date = dk

        for row in rows:
            feed_id = row[2]
            feed_name = row[3] or feed_id
            id_to_name[feed_id] = feed_name
            if feed_id not in items:
                items[feed_id] = []
            items[feed_id].append(
                RSSItem(
                    title=row[1],
                    feed_id=feed_id,
                    feed_name=feed_name,
                    url=row[4] or "",
                    published_at=row[5] or "",
                    summary=row[6] or "",
                    author=row[7] or "",
                    crawl_time=row[9],
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                )
            )

        cursor.execute(
            """
            SELECT cs.feed_id
            FROM rss_crawl_status cs
            JOIN rss_crawl_records cr ON cs.crawl_record_id = cr.id
            WHERE cs.day_key = %s AND cr.day_key = %s
              AND cr.crawl_time = %s AND cs.status = 'failed'
            """,
            (dk, dk, latest_time),
        )
        failed_ids = [row[0] for row in cursor.fetchall()]

        return RSSData(
            date=crawl_date,
            crawl_time=latest_time,
            items=items,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
        )
    except Exception as e:
        print(f"[存储] 获取最新 RSS 数据失败: {e}")
        return None
