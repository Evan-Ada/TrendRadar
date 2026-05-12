-- TrendRadar MySQL RSS 表结构（单库 + day_key）
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS rss_feeds (
    day_key CHAR(10) NOT NULL,
    id VARCHAR(191) NOT NULL,
    name VARCHAR(512) NOT NULL,
    feed_url VARCHAR(1024) DEFAULT '',
    is_active TINYINT DEFAULT 1,
    last_fetch_time VARCHAR(64) NULL,
    last_fetch_status VARCHAR(32) NULL,
    item_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (day_key, id),
    KEY idx_rss_feeds_day (day_key)
);

CREATE TABLE IF NOT EXISTS rss_items (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    title TEXT NOT NULL,
    feed_id VARCHAR(191) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    published_at VARCHAR(64) NULL,
    summary TEXT NULL,
    author VARCHAR(512) NULL,
    first_crawl_time VARCHAR(32) NOT NULL,
    last_crawl_time VARCHAR(32) NOT NULL,
    crawl_count INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_day_url_feed (day_key, url(512), feed_id),
    KEY idx_rss_feed (feed_id),
    KEY idx_rss_published (published_at),
    KEY idx_rss_crawl_time (last_crawl_time),
    KEY idx_rss_title (title(191)),
    KEY idx_rss_day (day_key)
);

CREATE TABLE IF NOT EXISTS rss_crawl_records (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    crawl_time VARCHAR(32) NOT NULL,
    total_items INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rss_day_crawl (day_key, crawl_time),
    KEY idx_rss_crawl_day (day_key)
);

CREATE TABLE IF NOT EXISTS rss_crawl_status (
    day_key CHAR(10) NOT NULL,
    crawl_record_id BIGINT NOT NULL,
    feed_id VARCHAR(191) NOT NULL,
    status VARCHAR(16) NOT NULL,
    error_message TEXT NULL,
    PRIMARY KEY (crawl_record_id, feed_id),
    KEY idx_rss_cs_day (day_key),
    CONSTRAINT fk_rss_cs_record FOREIGN KEY (crawl_record_id) REFERENCES rss_crawl_records (id) ON DELETE CASCADE
);
