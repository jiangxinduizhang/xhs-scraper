"""
开盘啦任务执行器。

这一层只做任务编排和结果落盘，不直接承载解析规则。
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
import shutil

from src import config
from src.apps.kaipanla.manifest import build_stub_manifest
from src.apps.kaipanla.report import write_run_report
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.controller.device import clear_proxy, configure_proxy, connect_device, launch_app, preflight_check
from src.proxy.parser import XHSParser


class KaipanlaRunner:
    """执行单个开盘啦任务。"""

    def __init__(self, task: TaskSpec):
        self.task = task
        self.parser = XHSParser()
        self._device = None
        self._proxy_process: subprocess.Popen | None = None
        self._started_at = datetime.now()
        self._raw_path = self._resolve_raw_path()
        self._raw_line_count_before = self._count_raw_lines(self._raw_path)

    @property
    def device(self):
        if self._device is None:
            self._device = connect_device()
        return self._device

    def run(self) -> RunResult:
        self._archive_previous_artifacts()
        self.task.save(self._resolve_task_path())
        result = RunResult(
            task_id=self.task.task_id,
            app=self.task.app,
            page=self.task.page,
            goal=self.task.goal,
            started_at=self._started_at.isoformat(timespec="seconds"),
            db_path=self.task.db_path,
            next_action=self.task.next_action_hint,
        )

        try:
            self._prepare(result)
            self._record_step(result, "app_started", self.task.package_name)
            self._run_task(result)
            self._record_step(result, "page_flow_complete", self.task.page)
            time.sleep(2)
            result.captured_count = max(0, self._count_raw_lines(self._raw_path) - self._raw_line_count_before)
            result.raw_paths = [str(self._raw_path)] if self._raw_path.exists() else []
            parsed_items = self._parse_recent_raw_items()
            result.parsed_count = len(parsed_items)
            result.source_counts = dict(Counter(item.source or "unknown" for item in parsed_items))
            result.note_type_counts = dict(Counter(item.note_type for item in parsed_items))
            if result.captured_count > 0:
                self._record_step(result, "request_captured", str(result.captured_count))
            if result.parsed_count > 0:
                self._record_step(result, "parsed_complete", str(result.parsed_count))
            result.status = "success" if result.captured_count > 0 else "partial"
        except Exception as exc:
            result.status = "failed"
            result.error = f"{type(exc).__name__}: {exc}"
            result.next_action = self.task.next_action_hint or "检查环境和页面路径"
        finally:
            result.finished_at = datetime.now().isoformat(timespec="seconds")
            result.duration_sec = (datetime.now() - self._started_at).total_seconds()
            self._cleanup()
            report_path = self._resolve_report_path()
            write_run_report(self.task, result, report_path)
            result.report_path = str(report_path)
            self._record_step(result, "report_written", str(report_path))
            result.save(self._resolve_run_path())
            self._record_step(result, "run_written", str(self._resolve_run_path()))
            result.save(self._resolve_run_path())
        return result

    def _prepare(self, result: RunResult) -> None:
        self._start_proxy()
        self._record_step(result, "proxy_started", f"port={config.PROXY_PORT}")
        configure_proxy(config.PROXY_PORT)
        self._record_step(result, "proxy_configured", f"port={config.PROXY_PORT}")
        preflight_check()
        self._record_step(result, "preflight_ok", "adb reverse + proxy")
        launch_app(self.device, fresh_start=True, package=self.task.package_name, activity=self.task.launch_activity)
        self._record_step(result, "launch_app", f"{self.task.package_name} {self.task.launch_activity}")

    def _run_task(self, result: RunResult) -> None:
        if self.task.page == "market_emotion":
            self._run_market_emotion(result)
            return
        raise ValueError(f"暂不支持的页面任务: {self.task.page}")

    def _run_market_emotion(self, result: RunResult) -> None:
        d = self.device

        # 先回到可控起点，再点击“行情”进入目标区域。
        for _ in range(3):
            try:
                d.press("back")
                time.sleep(0.8)
            except Exception:
                break

        if not self._click_text(d, "首页", timeout=2):
            self._tap_center_fallback(d)
        self._record_step(result, "home_reached", "首页")
        time.sleep(1.0)
        self._click_text(d, "行情", timeout=3)
        self._record_step(result, "market_reached", "行情")
        time.sleep(2.0)
        self._click_text(d, "情绪", timeout=3)
        self._record_step(result, "emotion_reached", "情绪")
        time.sleep(2.0)

        # 轻微滚动，推动页面把更多数据项请求出来。
        for _ in range(2):
            d.swipe(d.window_size()[0] // 2, int(d.window_size()[1] * 0.75), d.window_size()[0] // 2, int(d.window_size()[1] * 0.40), duration=0.25)
            time.sleep(1.0)

    def _start_proxy(self) -> None:
        manifest = build_stub_manifest()
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
        env["XHS_DB_PATH"] = self.task.db_path
        env["SAVE_FIXTURE"] = "true"
        env["TARGET_HOSTS"] = ",".join(sorted(manifest.target_hosts))
        env["TARGET_PATHS"] = ",".join(manifest.target_paths)
        log_path = Path("logs")
        log_path.mkdir(parents=True, exist_ok=True)
        proxy_log = log_path / f"{self.task.task_id}.mitmdump.log"
        self._kill_existing_proxy()
        with proxy_log.open("w", encoding="utf-8") as f:
            self._proxy_process = subprocess.Popen(
                ["mitmdump", "-p", str(config.PROXY_PORT), "-s", "src/proxy/addon.py"],
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
            )
        time.sleep(2)
        if self._proxy_process.poll() is not None:
            raise RuntimeError(f"mitmdump 启动失败，请查看日志: {proxy_log}")

    def _cleanup(self) -> None:
        if self._proxy_process and self._proxy_process.poll() is None:
            self._proxy_process.terminate()
            try:
                self._proxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proxy_process.kill()
        clear_proxy(config.PROXY_PORT)

    @staticmethod
    def _kill_existing_proxy() -> None:
        subprocess.run(
            ["pkill", "-f", f"mitmdump -p {config.PROXY_PORT} -s src/proxy/addon.py"],
            capture_output=True,
            text=True,
        )

    def _parse_recent_raw_items(self) -> list:
        if not self._raw_path.exists():
            return []
        items = []
        lines = self._raw_path.read_text(encoding="utf-8").splitlines()
        recent = lines[self._raw_line_count_before:]
        for line in recent:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            path = record.get("path", "")
            data = record.get("data", {})
            if isinstance(data, dict):
                items.extend(self.parser.parse(path, data))
        return items

    def _resolve_raw_path(self) -> Path:
        return Path(self.task.raw_dir) / f"{self._started_at.strftime('%Y%m%d')}.jsonl"

    def _resolve_run_path(self) -> Path:
        return Path(self.task.runs_dir) / f"{self.task.task_id}.json"

    def _resolve_task_path(self) -> Path:
        return Path(self.task.runs_dir) / f"{self.task.task_id}.task.json"

    def _resolve_report_path(self) -> Path:
        return Path(self.task.reports_dir) / f"{self.task.task_id}.md"

    def _archive_previous_artifacts(self) -> None:
        archive_root = Path(self.task.runs_dir) / "archive" / self.task.task_id / self._started_at.strftime("%Y%m%d-%H%M%S")
        self._archive_if_exists(self._resolve_task_path(), archive_root)
        self._archive_if_exists(self._resolve_run_path(), archive_root)
        self._archive_if_exists(self._resolve_report_path(), archive_root)

    @staticmethod
    def _archive_if_exists(path: Path, archive_root: Path) -> None:
        if not path.exists():
            return
        archive_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(archive_root / path.name))

    @staticmethod
    def _count_raw_lines(path: Path) -> int:
        if not path.exists():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    @staticmethod
    def _click_text(d, text: str, timeout: float = 2.0) -> bool:
        try:
            node = d(text=text)
            if node.exists(timeout=timeout):
                node.click()
                time.sleep(0.8)
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def _tap_center_fallback(d) -> None:
        width, height = d.window_size()
        d.click(width // 2, int(height * 0.08))

    @staticmethod
    def _record_step(result: RunResult | None, name: str, detail: str = "") -> None:
        event = {
            "name": name,
            "detail": detail,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        if result is not None:
            result.step_events.append(event)


def run_task(task: TaskSpec) -> RunResult:
    return KaipanlaRunner(task).run()
