"""
mitmproxy addon - 小红书 API 数据拦截
用法：mitmdump -p 8080 -s src/proxy/addon.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# mitmproxy 使用独立 Python 环境，需要手动把项目根目录加入 sys.path
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from typing import TYPE_CHECKING

from src import config
from src.proxy.parser import XHSParser
from src.storage.db import Database

if TYPE_CHECKING:
    from mitmproxy.http import HTTPFlow

log = logging.getLogger(__name__)


class XHSAddon:
    """
    懒加载设计：Database 和 Parser 在首次使用时初始化，
    避免 import 时产生副作用（便于单元测试）
    """
    def __init__(self):
        self._db: Database | None = None
        self._parser: XHSParser | None = None

    @property
    def db(self) -> Database:
        if self._db is None:
            db_path = os.getenv("XHS_DB_PATH", "data/xiaohongshu.db")
            self._db = Database(db_path)
        return self._db

    @property
    def parser(self) -> XHSParser:
        if self._parser is None:
            self._parser = XHSParser()
        return self._parser

    def response(self, flow):
        """mitmproxy 每次收到响应时调用"""
        if not self._is_target(flow):
            return

        try:
            body = flow.response.get_text()
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        except Exception as e:
            log.error(f"读取响应失败 {flow.request.url}: {e}")
            return

        path = flow.request.path.split("?")[0]

        try:
            items = self.parser.parse(path, data)
            if items:
                self.db.save(items)
                log.info(f"已保存 {len(items)} 条: {path}")
        except Exception as e:
            log.error(f"解析/存储失败 {path}: {e}")

        if os.getenv("SAVE_FIXTURE") == "true":
            self._save_raw(path, data)

    def _is_target(self, flow) -> bool:
        """判断是否为目标请求（支持多 host）"""
        if flow.request.host not in config.TARGET_HOSTS:
            return False
        path = flow.request.path.split("?")[0]
        return any(path.startswith(p) for p in config.TARGET_PATHS)

    def _save_raw(self, path: str, data: dict):
        """保存原始响应到 JSONL（调试 / 生成 fixture 用）"""
        os.makedirs("data/raw", exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"data/raw/{date_str}.jsonl"
        record = {
            "ts": datetime.now().isoformat(),
            "path": path,
            "data": data,
        }
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# mitmproxy 入口
addons = [XHSAddon()]
