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
import xml.etree.ElementTree as ET

from src import config
from src.apps.kaipanla.manifest import build_stub_manifest
from src.apps.kaipanla.pages import get_page_spec
from src.apps.kaipanla.report import write_run_report
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.controller.device import (
    PreflightError,
    capture_screenshot,
    capture_ui_dump,
    capture_visible_text,
    clear_proxy,
    configure_proxy,
    connect_device,
    launch_app,
    preflight_check,
)
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
            round_index=self.task.round_index,
            max_rounds=self.task.max_rounds,
            session_id=self.task.session_id,
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
        except PreflightError as exc:
            result.status = "failed"
            result.error = f"{type(exc).__name__}: {exc}"
            result.next_action = exc.recover_hint or self.task.next_action_hint or "检查环境和页面路径"
            result.source_counts = {
                "error_code": exc.code,
                "error_stage": "preflight",
            }
            self._record_step(result, "preflight_failed", exc.code)
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
        preflight = preflight_check()
        self._record_step(result, "preflight_ok", json.dumps(preflight, ensure_ascii=False, sort_keys=True))
        launch_app(self.device, fresh_start=True, package=self.task.package_name, activity=self.task.launch_activity)
        self._record_step(result, "launch_app", f"{self.task.package_name} {self.task.launch_activity}")

    def _run_task(self, result: RunResult) -> None:
        spec = get_page_spec(self.task.page)
        steps = self.task.action_plan or spec.navigation_steps
        self._run_navigation(result, steps)

    def _run_navigation(self, result: RunResult, steps: list[dict]) -> None:
        d = self.device
        for index, step in enumerate(steps, start=1):
            action = str(step.get("action") or "")
            action_id = str(step.get("name") or f"step_{index}")
            self._record_step(result, "action_started", action_id, {
                "action": action,
                "index": index,
                "round_index": self.task.round_index,
            })

            before = self._capture_action_evidence(result, action_id, phase="before")
            executed = False
            found = None
            error = ""
            try:
                if action == "back":
                    executed = True
                    for _ in range(int(step.get("times", 1))):
                        try:
                            d.press("back")
                            time.sleep(float(step.get("sleep", 0.8)))
                        except Exception:
                            break
                elif action == "tap_text":
                    tap_target = str(step.get("text") or step.get("target") or "")
                    found = self._click_text(d, tap_target, timeout=float(step.get("timeout", 2.0)))
                    executed = bool(found)
                elif action == "tap_text_or_fallback":
                    tap_target = str(step.get("text") or step.get("target") or "")
                    found = self._click_text(d, tap_target, timeout=float(step.get("timeout", 2.0)))
                    if found:
                        executed = True
                    else:
                        self._tap_center_fallback(d)
                        executed = True
                elif action == "record":
                    executed = True
                    self._record_step(result, str(step.get("name", "step")), str(step.get("detail", "")))
                elif action == "sleep":
                    executed = True
                    time.sleep(float(step.get("seconds", 1.0)))
                elif action == "swipe_up":
                    executed = True
                    for _ in range(int(step.get("times", 1))):
                        width, height = d.window_size()
                        d.swipe(width // 2, int(height * 0.75), width // 2, int(height * 0.40), duration=0.25)
                        time.sleep(float(step.get("sleep", 1.0)))
                else:
                    raise ValueError(f"unsupported navigation action: {action}")
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                after = self._capture_action_evidence(result, action_id, phase="after")
                self._record_step(result, "action_finished", action_id, {
                    "action": action,
                    "index": index,
                    "found": found,
                    "executed": executed,
                    "error": error,
                    "before": before,
                    "after": after,
                })

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

    def _capture_action_evidence(self, result: RunResult, action_id: str, phase: str) -> dict:
        capture_options = self.task.capture_options or {}
        out: dict = {
            "phase": phase,
            "action_id": action_id,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
        }
        artifact_root = Path(self.task.runs_dir) / "artifacts" / self.task.task_id
        artifact_root.mkdir(parents=True, exist_ok=True)

        if capture_options.get("screenshot_before_after", False):
            screenshot_path = artifact_root / f"{action_id}-{phase}.png"
            out["screenshot"] = capture_screenshot(self.device, screenshot_path)

        if capture_options.get("ui_dump_before_after", False):
            ui_dump_path = artifact_root / f"{action_id}-{phase}.xml"
            out["ui_dump"] = capture_ui_dump(self.device, ui_dump_path)

        if capture_options.get("visible_text_before_after", False):
            out["visible_text"] = capture_visible_text(self.device)

        result.artifacts.setdefault("action_evidence", []).append(out)
        return out

    @staticmethod
    def _click_text(d, text: str, timeout: float = 2.0) -> bool:
        target = (text or "").strip()
        if not target:
            return False

        selectors = [
            {"text": target},
            {"textContains": target},
            {"description": target},
            {"descriptionContains": target},
        ]
        if target == "龙虎榜":
            selectors.extend([
                {"text": "龙虎榜\nCharts"},
                {"textContains": "龙虎榜\nCharts"},
                {"textContains": "实时龙虎榜"},
            ])

        for selector in selectors:
            try:
                node = d(**selector)
                if not node.exists(timeout=timeout):
                    continue
                current = node
                for _ in range(4):
                    info = current.info
                    if info.get("clickable"):
                        current.click()
                        time.sleep(0.8)
                        return True
                    current = current.parent()
                    if current is None:
                        break
                node.click()
                time.sleep(0.8)
                return True
            except Exception:
                continue

        try:
            xml = d.dump_hierarchy(compressed=False)
            bounds = KaipanlaRunner._find_text_bounds_in_xml(xml, target)
            if bounds:
                x1, y1, x2, y2 = bounds
                d.click((x1 + x2) // 2, (y1 + y2) // 2)
                time.sleep(0.8)
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def _find_text_bounds_in_xml(xml_text: str, target: str) -> tuple[int, int, int, int] | None:
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return None

        def parse_bounds(raw: str) -> tuple[int, int, int, int] | None:
            try:
                raw = (raw or "").strip()
                left, right = raw.split("][")
                x1, y1 = left.lstrip("[").split(",")
                x2, y2 = right.rstrip("]").split(",")
                return int(x1), int(y1), int(x2), int(y2)
            except Exception:
                return None

        best = None
        best_area = -1
        for node in root.iter("node"):
            text_val = str(node.attrib.get("text") or "")
            desc_val = str(node.attrib.get("content-desc") or "")
            if target not in text_val and target not in desc_val:
                continue
            bounds = parse_bounds(node.attrib.get("bounds", ""))
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            area = max(0, x2 - x1) * max(0, y2 - y1)
            if area > best_area:
                best = bounds
                best_area = area
        return best

    @staticmethod
    def _tap_center_fallback(d) -> None:
        width, height = d.window_size()
        d.click(width // 2, int(height * 0.08))

    @staticmethod
    def _record_step(result: RunResult | None, name: str, detail: str = "", extra: dict | None = None) -> None:
        event = {
            "name": name,
            "detail": detail,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        if extra:
            event.update(extra)
        if result is not None:
            result.step_events.append(event)


def run_task(task: TaskSpec) -> RunResult:
    return KaipanlaRunner(task).run()
