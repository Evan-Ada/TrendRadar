# coding=utf-8
"""
MySQL 存储后端：热榜 + RSS + AI 筛选数据写入同一 MySQL 库（按 day_key 区分日历日）。
HTML/TXT 仍写入本地 data_dir。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pymysql

from trendradar.storage.base import StorageBackend, NewsData, RSSData, RSSItem
from trendradar.storage.mysql_mixin import MySQLStorageMixin
from trendradar.utils.time import (
    DEFAULT_TIMEZONE,
    get_configured_time,
    format_date_folder,
    format_time_filename,
)


class MySQLStorageBackend(MySQLStorageMixin, StorageBackend):
    """使用 pymysql 连接 MySQL；表结构见 mysql_schema.sql / mysql_rss_schema.sql / mysql_ai_filter_schema.sql。"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        data_dir: str = "output",
        enable_txt: bool = True,
        enable_html: bool = True,
        timezone: str = DEFAULT_TIMEZONE,
        charset: str = "utf8mb4",
    ):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.database = database
        self.data_dir = Path(data_dir)
        self.enable_txt = enable_txt
        self.enable_html = enable_html
        self.timezone = timezone
        self.charset = charset

        self._conn: Optional[pymysql.connections.Connection] = None
        self._schema_initialized = False

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            autocommit=False,
            cursorclass=pymysql.cursors.Cursor,
        )

    def _ensure_schema(self) -> None:
        if self._schema_initialized:
            return
        if self._conn is None:
            self._conn = self._connect()
        self._init_tables(self._conn, db_type="all")
        self._schema_initialized = True

    def _get_connection(self, date: Optional[str] = None, db_type: str = "news"):
        self._ensure_schema()
        assert self._conn is not None
        return self._conn

    def _get_configured_time(self):
        return get_configured_time(self.timezone)

    def _format_date_folder(self, date: Optional[str] = None) -> str:
        return format_date_folder(date, self.timezone)

    def _format_time_filename(self) -> str:
        return format_time_filename(self.timezone)

    @property
    def backend_name(self) -> str:
        return "mysql"

    @property
    def supports_txt(self) -> bool:
        return self.enable_txt

    # --- 与 LocalStorageBackend 相同的 TXT/HTML 与委托逻辑（略去 docstring 重复）---

    def save_news_data(self, data: NewsData) -> bool:
        success, new_count, updated_count, title_changed_count, off_list_count = self._save_news_data_impl(
            data, "[MySQL存储]"
        )
        if success:
            parts = [f"[MySQL存储] 处理完成：新增 {new_count} 条"]
            if updated_count > 0:
                parts.append(f"更新 {updated_count} 条")
            if title_changed_count > 0:
                parts.append(f"标题变更 {title_changed_count} 条")
            if off_list_count > 0:
                parts.append(f"脱榜 {off_list_count} 条")
            print("，".join(parts))
        return success

    def get_today_all_data(self, date: Optional[str] = None):
        return self._get_today_all_data_impl(date)

    def get_latest_crawl_data(self, date: Optional[str] = None):
        return self._get_latest_crawl_data_impl(date)

    def detect_new_titles(self, current_data: NewsData) -> Dict[str, Dict]:
        return self._detect_new_titles_impl(current_data)

    def is_first_crawl_today(self, date: Optional[str] = None) -> bool:
        return self._is_first_crawl_today_impl(date)

    def get_crawl_times(self, date: Optional[str] = None) -> List[str]:
        return self._get_crawl_times_impl(date)

    def has_period_executed(self, date_str: str, period_key: str, action: str) -> bool:
        return self._has_period_executed_impl(date_str, period_key, action)

    def record_period_execution(self, date_str: str, period_key: str, action: str) -> bool:
        ok = self._record_period_execution_impl(date_str, period_key, action)
        if ok:
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[MySQL存储] 时间段执行记录已保存: {period_key}/{action} at {now_str}")
        return ok

    def save_rss_data(self, data: RSSData) -> bool:
        success, new_count, updated_count = self._save_rss_data_impl(data, "[MySQL存储]")
        if success:
            parts = [f"[MySQL存储] RSS 处理完成：新增 {new_count} 条"]
            if updated_count > 0:
                parts.append(f"更新 {updated_count} 条")
            print("，".join(parts))
        return success

    def get_rss_data(self, date: Optional[str] = None):
        return self._get_rss_data_impl(date)

    def detect_new_rss_items(self, current_data: RSSData) -> Dict[str, List[RSSItem]]:
        return self._detect_new_rss_items_impl(current_data)

    def get_latest_rss_data(self, date: Optional[str] = None):
        return self._get_latest_rss_data_impl(date)

    def get_active_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        return self._get_active_tags_impl(date, interests_file)

    def get_latest_prompt_hash(self, date=None, interests_file="ai_interests.txt"):
        return self._get_latest_prompt_hash_impl(date, interests_file)

    def get_latest_ai_filter_tag_version(self, date=None):
        return self._get_latest_tag_version_impl(date)

    def deprecate_all_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        return self._deprecate_all_tags_impl(date, interests_file)

    def save_ai_filter_tags(self, tags, version, prompt_hash, date=None, interests_file="ai_interests.txt"):
        return self._save_tags_impl(date, tags, version, prompt_hash, interests_file)

    def save_ai_filter_results(self, results, date=None):
        return self._save_filter_results_impl(date, results)

    def get_active_ai_filter_results(self, date=None, interests_file="ai_interests.txt"):
        return self._get_active_filter_results_impl(date, interests_file)

    def deprecate_specific_ai_filter_tags(self, tag_ids, date=None):
        return self._deprecate_specific_tags_impl(date, tag_ids)

    def update_ai_filter_tags_hash(self, interests_file, new_hash, date=None):
        return self._update_tags_hash_impl(date, interests_file, new_hash)

    def update_ai_filter_tag_descriptions(self, tag_updates, date=None, interests_file="ai_interests.txt"):
        return self._update_tag_descriptions_impl(date, tag_updates, interests_file)

    def update_ai_filter_tag_priorities(self, tag_priorities, date=None, interests_file="ai_interests.txt"):
        return self._update_tag_priorities_impl(date, tag_priorities, interests_file)

    def save_analyzed_news(self, news_ids, source_type, interests_file, prompt_hash, matched_ids, date=None):
        return self._save_analyzed_news_impl(date, news_ids, source_type, interests_file, prompt_hash, matched_ids)

    def get_analyzed_news_ids(self, source_type="hotlist", date=None, interests_file="ai_interests.txt"):
        return self._get_analyzed_news_ids_impl(date, source_type, interests_file)

    def clear_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        return self._clear_analyzed_news_impl(date, interests_file)

    def clear_unmatched_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        return self._clear_unmatched_analyzed_news_impl(date, interests_file)

    def get_all_news_ids(self, date=None):
        return self._get_all_news_ids_impl(date)

    def get_all_rss_ids(self, date=None):
        return self._get_all_rss_ids_impl(date)

    def save_txt_snapshot(self, data: NewsData) -> Optional[str]:
        if not self.enable_txt:
            return None
        try:
            date_folder = self._format_date_folder(data.date)
            txt_dir = self.data_dir / "txt" / date_folder
            txt_dir.mkdir(parents=True, exist_ok=True)
            file_path = txt_dir / f"{data.crawl_time}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                for source_id, news_list in data.items.items():
                    source_name = data.id_to_name.get(source_id, source_id)
                    if source_name and source_name != source_id:
                        f.write(f"{source_id} | {source_name}\n")
                    else:
                        f.write(f"{source_id}\n")
                    sorted_news = sorted(news_list, key=lambda x: x.rank)
                    for item in sorted_news:
                        line = f"{item.rank}. {item.title}"
                        if item.url:
                            line += f" [URL:{item.url}]"
                        if item.mobile_url:
                            line += f" [MOBILE:{item.mobile_url}]"
                        f.write(line + "\n")
                    f.write("\n")
                if data.failed_ids:
                    f.write("==== 以下ID请求失败 ====\n")
                    for failed_id in data.failed_ids:
                        f.write(f"{failed_id}\n")
            print(f"[MySQL存储] TXT 快照已保存: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[MySQL存储] 保存 TXT 快照失败: {e}")
            return None

    def save_html_report(self, html_content: str, filename: str) -> Optional[str]:
        if not self.enable_html:
            return None
        try:
            date_folder = self._format_date_folder()
            html_dir = self.data_dir / "html" / date_folder
            html_dir.mkdir(parents=True, exist_ok=True)
            file_path = html_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"[MySQL存储] HTML 报告已保存: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"[MySQL存储] 保存 HTML 报告失败: {e}")
            return None

    def cleanup(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                print("[MySQL存储] 已关闭数据库连接")
            except Exception as e:
                print(f"[MySQL存储] 关闭连接失败: {e}")
            self._conn = None

    def cleanup_old_data(self, retention_days: int) -> int:
        if retention_days <= 0:
            return 0
        cutoff = (self._get_configured_time() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
        deleted = 0
        try:
            self._ensure_schema()
            assert self._conn is not None
            cur = self._conn.cursor()
            tables_news = [
                "crawl_source_status",
                "crawl_records",
                "rank_history",
                "title_changes",
                "news_items",
                "platforms",
                "period_executions",
                "ai_filter_analyzed_news",
                "ai_filter_results",
                "ai_filter_tags",
            ]
            tables_rss = [
                "rss_crawl_status",
                "rss_crawl_records",
                "rss_items",
                "rss_feeds",
            ]
            for t in tables_news:
                cur.execute(f"DELETE FROM `{t}` WHERE day_key < %s", (cutoff,))
                deleted += cur.rowcount
            for t in tables_rss:
                cur.execute(f"DELETE FROM `{t}` WHERE day_key < %s", (cutoff,))
                deleted += cur.rowcount
            self._conn.commit()
            if deleted > 0:
                print(f"[MySQL存储] 清理 day_key < {cutoff} 的行（约 {deleted} 行）")
        except Exception as e:
            print(f"[MySQL存储] 清理过期数据失败: {e}")
        return deleted

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
