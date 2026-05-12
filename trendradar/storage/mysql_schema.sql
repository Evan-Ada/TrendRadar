-- TrendRadar MySQL 热榜库表结构（单库 + day_key 对应原按日 SQLite 文件）
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS platforms (
    day_key CHAR(10) NOT NULL,
    id VARCHAR(191) NOT NULL,
    name VARCHAR(512) NOT NULL,
    is_active TINYINT DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (day_key, id),
    KEY idx_platforms_day (day_key)
);

CREATE TABLE IF NOT EXISTS news_items (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    title TEXT NOT NULL,
    platform_id VARCHAR(191) NOT NULL,
    `rank` INT NOT NULL,
    url VARCHAR(2048) NULL,
    mobile_url VARCHAR(1024) NULL,
    snippet TEXT NULL,
    first_crawl_time VARCHAR(32) NOT NULL,
    last_crawl_time VARCHAR(32) NOT NULL,
    crawl_count INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_day_plat_url (day_key, platform_id, url(512)),
    KEY idx_news_day (day_key),
    KEY idx_news_platform (platform_id),
    KEY idx_news_crawl_time (last_crawl_time),
    KEY idx_news_title (title(191)),
    CONSTRAINT fk_news_platform FOREIGN KEY (day_key, platform_id)
        REFERENCES platforms (day_key, id)
);

CREATE TABLE IF NOT EXISTS title_changes (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    news_item_id BIGINT NOT NULL,
    old_title TEXT NOT NULL,
    new_title TEXT NOT NULL,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_title_changes_day (day_key),
    KEY idx_title_changes_news (news_item_id),
    CONSTRAINT fk_title_news FOREIGN KEY (news_item_id) REFERENCES news_items (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rank_history (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    news_item_id BIGINT NOT NULL,
    `rank` INT NOT NULL,
    crawl_time VARCHAR(32) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_rank_day (day_key),
    KEY idx_rank_news (news_item_id),
    CONSTRAINT fk_rank_news FOREIGN KEY (news_item_id) REFERENCES news_items (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS crawl_records (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    crawl_time VARCHAR(32) NOT NULL,
    total_items INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_day_crawl (day_key, crawl_time),
    KEY idx_crawl_day (day_key)
);

CREATE TABLE IF NOT EXISTS crawl_source_status (
    day_key CHAR(10) NOT NULL,
    crawl_record_id BIGINT NOT NULL,
    platform_id VARCHAR(191) NOT NULL,
    status VARCHAR(16) NOT NULL,
    PRIMARY KEY (crawl_record_id, platform_id),
    KEY idx_css_day (day_key),
    CONSTRAINT fk_css_record FOREIGN KEY (crawl_record_id) REFERENCES crawl_records (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS period_executions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    day_key CHAR(10) NOT NULL,
    execution_date CHAR(10) NOT NULL,
    period_key VARCHAR(191) NOT NULL,
    action VARCHAR(32) NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_period (day_key, execution_date, period_key, action),
    KEY idx_period_lookup (day_key, execution_date, period_key, action)
);
