-- 如果 personal_website 数据库不存在，就创建它
CREATE DATABASE IF NOT EXISTS personal_website DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 切换到 personal_website 数据库
USE personal_website;

-- 如果 profile 表不存在，就创建它
CREATE TABLE IF NOT EXISTS profile (
  id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键 ID',
  name VARCHAR(100) NOT NULL COMMENT '姓名',
  title VARCHAR(150) NOT NULL COMMENT '个人标题',
  description TEXT NOT NULL COMMENT '个人介绍',
  github VARCHAR(255) NOT NULL COMMENT 'GitHub 链接',
  email VARCHAR(150) NOT NULL COMMENT '邮箱'
) COMMENT='个人网站基础信息表';

-- 插入一条测试数据，如果 id=1 已存在就更新它
INSERT INTO profile (id, name, title, description, github, email)
VALUES (1, '我的名字', '全栈开发学习者', '这是我的个人网站，当前正在从 0 到 1 搭建中。', 'https://github.com/yourname', 'your@email.com')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  title = VALUES(title),
  description = VALUES(description),
  github = VALUES(github),
  email = VALUES(email);
