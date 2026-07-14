-- v3 功能表和字段参考。
-- 正常情况下不需要手动执行，后端启动时会自动建表和补字段。

USE personal_website;

ALTER TABLE articles ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'published';
ALTER TABLE articles ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE articles ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE articles ADD COLUMN deleted_at DATETIME NULL;

ALTER TABLE posts ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE posts ADD COLUMN deleted_at DATETIME NULL;

ALTER TABLE post_comments ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE post_comments ADD COLUMN deleted_at DATETIME NULL;

ALTER TABLE article_comments ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE article_comments ADD COLUMN deleted_at DATETIME NULL;

CREATE TABLE IF NOT EXISTS messages (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  nickname VARCHAR(80) NOT NULL DEFAULT '游客',
  content TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'published',
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL
) COMMENT='留言板';

CREATE TABLE IF NOT EXISTS post_likes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  post_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_post_like (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS article_likes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  article_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_article_like (article_id, user_id)
);

CREATE TABLE IF NOT EXISTS article_favorites (
  id INT PRIMARY KEY AUTO_INCREMENT,
  article_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_article_favorite (article_id, user_id)
);

CREATE TABLE IF NOT EXISTS novel_favorites (
  id INT PRIMARY KEY AUTO_INCREMENT,
  novel_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_novel_favorite (novel_id, user_id)
);

CREATE TABLE IF NOT EXISTS reading_progress (
  id INT PRIMARY KEY AUTO_INCREMENT,
  novel_id INT NOT NULL,
  user_id INT NOT NULL,
  progress INT NOT NULL DEFAULT 0,
  font_size INT NOT NULL DEFAULT 18,
  theme VARCHAR(20) NOT NULL DEFAULT 'dark',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_reading_progress (novel_id, user_id)
);
