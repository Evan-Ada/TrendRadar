# coding=utf-8
"""
MySQL 存储 Mixin：委托 mysql_news / mysql_rssdata / mysql_aifilter 实现具体 SQL。
"""

from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from trendradar.storage import mysql_aifilter, mysql_news, mysql_rssdata
from trendradar.storage.base import NewsData, RSSData, RSSItem
from trendradar.storage.mysql_util import run_mysql_script


class MySQLStorageMixin:
    """
    子类需实现：
    - _get_connection(date, db_type) -> pymysql Connection（同一物理库即可）
    - _get_configured_time() / _format_date_folder / _format_time_filename
    - _ensure_schema() 在首次连接后创建表（由 MySQLStorageBackend 实现）
    """

    @abstractmethod
    def _get_connection(self, date: Optional[str] = None, db_type: str = "news"):
        pass

    @abstractmethod
    def _get_configured_time(self) -> datetime:
        pass

    @abstractmethod
    def _format_date_folder(self, date: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def _format_time_filename(self) -> str:
        pass

    def _init_tables(self, conn, db_type: str = "news") -> None:
        """供首次建库调用：执行 MySQL DDL 文件。"""
        base = Path(__file__).parent
        if db_type == "rss":
            paths = [base / "mysql_rss_schema.sql"]
        elif db_type == "news":
            paths = [base / "mysql_schema.sql", base / "mysql_ai_filter_schema.sql"]
        else:
            paths = [base / "mysql_schema.sql", base / "mysql_ai_filter_schema.sql", base / "mysql_rss_schema.sql"]

        cur = conn.cursor()
        for p in paths:
            if not p.exists():
                raise FileNotFoundError(f"MySQL schema 缺失: {p}")
            run_mysql_script(cur, p.read_text(encoding="utf-8"))
        conn.commit()

    def _save_news_data_impl(self, data: NewsData, log_prefix: str = "[存储]") -> tuple[bool, int, int, int, int]:
        return mysql_news.save_news_data_impl(self, data, log_prefix)

    def _get_today_all_data_impl(self, date: Optional[str] = None):
        return mysql_news.get_today_all_data_impl(self, date)

    def _get_latest_crawl_data_impl(self, date: Optional[str] = None):
        return mysql_news.get_latest_crawl_data_impl(self, date)

    def _detect_new_titles_impl(self, current_data: NewsData) -> Dict[str, Dict]:
        return mysql_news.detect_new_titles_impl(self, current_data)

    def _is_first_crawl_today_impl(self, date: Optional[str] = None) -> bool:
        return mysql_news.is_first_crawl_today_impl(self, date)

    def _get_crawl_times_impl(self, date: Optional[str] = None) -> List[str]:
        return mysql_news.get_crawl_times_impl(self, date)

    def _has_period_executed_impl(self, date_str: str, period_key: str, action: str) -> bool:
        return mysql_news.has_period_executed_impl(self, date_str, period_key, action)

    def _record_period_execution_impl(self, date_str: str, period_key: str, action: str) -> bool:
        return mysql_news.record_period_execution_impl(self, date_str, period_key, action)

    def _save_rss_data_impl(self, data: RSSData, log_prefix: str = "[存储]") -> tuple[bool, int, int]:
        return mysql_rssdata.save_rss_data_impl(self, data, log_prefix)

    def _get_rss_data_impl(self, date: Optional[str] = None):
        return mysql_rssdata.get_rss_data_impl(self, date)

    def _detect_new_rss_items_impl(self, current_data: RSSData) -> Dict[str, List[RSSItem]]:
        return mysql_rssdata.detect_new_rss_items_impl(self, current_data)

    def _get_latest_rss_data_impl(self, date: Optional[str] = None):
        return mysql_rssdata.get_latest_rss_data_impl(self, date)

    def _get_active_tags_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt"):
        return mysql_aifilter.get_active_tags_impl(self, date, interests_file)

    def _get_latest_prompt_hash_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt"):
        return mysql_aifilter.get_latest_prompt_hash_impl(self, date, interests_file)

    def _get_latest_tag_version_impl(self, date: Optional[str] = None) -> int:
        return mysql_aifilter.get_latest_tag_version_impl(self, date)

    def _deprecate_all_tags_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> int:
        return mysql_aifilter.deprecate_all_tags_impl(self, date, interests_file)

    def _save_tags_impl(
        self, date: Optional[str], tags: List[Dict], version: int, prompt_hash: str, interests_file: str = "ai_interests.txt"
    ) -> int:
        return mysql_aifilter.save_tags_impl(self, date, tags, version, prompt_hash, interests_file)

    def _deprecate_specific_tags_impl(self, date: Optional[str], tag_ids: List[int]) -> int:
        return mysql_aifilter.deprecate_specific_tags_impl(self, date, tag_ids)

    def _update_tags_hash_impl(self, date: Optional[str], interests_file: str, new_hash: str) -> int:
        return mysql_aifilter.update_tags_hash_impl(self, date, interests_file, new_hash)

    def _update_tag_descriptions_impl(self, date: Optional[str], tag_updates: List[Dict], interests_file: str = "ai_interests.txt") -> int:
        return mysql_aifilter.update_tag_descriptions_impl(self, date, tag_updates, interests_file)

    def _update_tag_priorities_impl(self, date: Optional[str], tag_priorities: List[Dict], interests_file: str = "ai_interests.txt") -> int:
        return mysql_aifilter.update_tag_priorities_impl(self, date, tag_priorities, interests_file)

    def _save_analyzed_news_impl(
        self, date: Optional[str], news_ids: List[int], source_type: str, interests_file: str, prompt_hash: str, matched_ids: set
    ) -> int:
        return mysql_aifilter.save_analyzed_news_impl(self, date, news_ids, source_type, interests_file, prompt_hash, matched_ids)

    def _get_analyzed_news_ids_impl(self, date: Optional[str] = None, source_type: str = "hotlist", interests_file: str = "ai_interests.txt") -> Set[int]:
        return mysql_aifilter.get_analyzed_news_ids_impl(self, date, source_type, interests_file)

    def _clear_analyzed_news_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> int:
        return mysql_aifilter.clear_analyzed_news_impl(self, date, interests_file)

    def _clear_unmatched_analyzed_news_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> int:
        return mysql_aifilter.clear_unmatched_analyzed_news_impl(self, date, interests_file)

    def _save_filter_results_impl(self, date: Optional[str], results: List[Dict]) -> int:
        return mysql_aifilter.save_filter_results_impl(self, date, results)

    def _get_active_filter_results_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> List[Dict]:
        return mysql_aifilter.get_active_filter_results_impl(self, date, interests_file)

    def _get_all_news_ids_impl(self, date: Optional[str] = None) -> List[Dict]:
        return mysql_aifilter.get_all_news_ids_impl(self, date)

    def _get_all_rss_ids_impl(self, date: Optional[str] = None) -> List[Dict]:
        return mysql_aifilter.get_all_rss_ids_impl(self, date)
