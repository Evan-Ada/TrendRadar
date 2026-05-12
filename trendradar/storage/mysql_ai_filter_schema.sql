-- AI 筛选表（MySQL，带 day_key）
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS ai_filter_tags (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    tag VARCHAR(512) NOT NULL,
    description TEXT,
    priority INT NOT NULL DEFAULT 9999,
    status VARCHAR(32) DEFAULT 'active',
    deprecated_at VARCHAR(64) NULL,
    version INT NOT NULL,
    prompt_hash VARCHAR(512) NOT NULL,
    interests_file VARCHAR(255) NOT NULL DEFAULT 'ai_interests.txt',
    created_at VARCHAR(32) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_ai_tags_day (day_key),
    KEY idx_ai_filter_tags_status (status),
    KEY idx_ai_filter_tags_version (version),
    KEY idx_ai_filter_tags_file (interests_file, status),
    KEY idx_ai_filter_tags_priority (interests_file, status, priority)
);

CREATE TABLE IF NOT EXISTS ai_filter_results (
    day_key CHAR(10) NOT NULL,
    id BIGINT NOT NULL AUTO_INCREMENT,
    news_item_id BIGINT NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'hotlist',
    tag_id BIGINT NOT NULL,
    relevance_score DOUBLE DEFAULT 0,
    status VARCHAR(32) DEFAULT 'active',
    deprecated_at VARCHAR(64) NULL,
    created_at VARCHAR(32) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_result (day_key, news_item_id, source_type, tag_id),
    KEY idx_ai_filter_results_status (status),
    KEY idx_ai_filter_results_news (news_item_id, source_type),
    KEY idx_ai_filter_results_tag (tag_id)
);

CREATE TABLE IF NOT EXISTS ai_filter_analyzed_news (
    day_key CHAR(10) NOT NULL,
    news_item_id BIGINT NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'hotlist',
    interests_file VARCHAR(255) NOT NULL DEFAULT 'ai_interests.txt',
    prompt_hash VARCHAR(512) NOT NULL,
    matched TINYINT NOT NULL DEFAULT 0,
    created_at VARCHAR(32) NOT NULL,
    PRIMARY KEY (day_key, news_item_id, source_type, interests_file),
    KEY idx_analyzed_news_lookup (source_type, interests_file),
    KEY idx_analyzed_news_hash (interests_file, prompt_hash)
);
