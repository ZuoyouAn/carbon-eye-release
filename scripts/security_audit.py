#!/usr/bin/env python3
"""Create a release-oriented secret and path audit without exposing values."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["backend", "frontend", "scripts", "tests", "docs", "README.md", "render.yaml", "netlify.toml"]
EXCLUDED_PARTS = {"node_modules", "dist", ".npm-cache", ".netlify", ".git", ".venv", "__pycache__", "logs", "outputs"}
RULES = {
    "疑似访问令牌": re.compile(r"(?i)(ghp_[a-z0-9_\-]+|github_pat_[a-z0-9_\-]+|ntlf_[a-z0-9_\-]+|rnd_[a-z0-9_\-]+)"),
    "疑似硬编码密码": re.compile(r"(?i)(password|passwd|secret)\s*[=:]\s*['\"][^'\"]{4,}['\"]"),
    "疑似令牌字面量": re.compile(r"(?i)(aqicn_token|waqi_token|api_key)\s*[=:]\s*['\"][^'\"$]{8,}['\"]"),
    "Windows 绝对路径": re.compile(r"[A-Za-z]:\\\\"),
}


def iter_files():
    for target in TARGETS:
        path = ROOT / target
        if path.is_file():
            yield path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and not (set(candidate.parts) & EXCLUDED_PARTS):
                    yield candidate


def main() -> None:
    findings: dict[str, list[str]] = {category: [] for category in RULES}
    scanned = 0
    for path in iter_files():
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".xlsx", ".xls"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for category, pattern in RULES.items():
            if pattern.search(content):
                findings[category].append(path.relative_to(ROOT).as_posix())

    lines = [
        "# 发布安全审计",
        "",
        f"- 审计时间：{datetime.now().astimezone().isoformat()}",
        f"- 扫描文本文件：{scanned}",
        "- 扫描范围：发布源码、构建配置、测试、文档与数据构建脚本。",
        "- 报告只记录路径与类别，不输出任何疑似凭据内容。",
        "",
        "## 结果",
    ]
    total = 0
    for category, paths in findings.items():
        unique_paths = sorted(set(paths))
        total += len(unique_paths)
        lines.append(f"- {category}：{'无' if not unique_paths else ', '.join(f'`{item}`' for item in unique_paths)}")
    lines.extend([
        "",
        "## 发布前控制",
        "- `.env`、部署缓存、构建产物、日志和本地数据输出均由 `.gitignore` 排除。",
        "- `AQICN_TOKEN` 仅允许在 Render 环境变量中配置，源码和静态 JSON 不保存其值。",
        "- 发布前应确认暂存区不包含本地运行日志、数据库文件、个人资料或部署信息文件。",
        "",
        f"审计结论：{'需修复后发布' if total else '未发现高置信度公开凭据或本地绝对路径。'}",
    ])
    (ROOT / "SECURITY_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"security_findings={total}")


if __name__ == "__main__":
    main()
