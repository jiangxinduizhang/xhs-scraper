from types import SimpleNamespace

from src.apps.kaipanla.entry import build_report, render_action_plan, render_environment_check, main
from src.apps.kaipanla.task import TaskSpec


class TestKaipanlaEntry:
    def test_action_plan_mentions_missing_fields(self):
        report = render_action_plan()
        assert "已就绪" in report
        assert "缺失字段: 无" in report
        assert "市场情绪" in report
        assert "行情 / 自选股 / 龙虎榜" in report

    def test_action_plan_mentions_immediate_commands(self):
        report = render_action_plan()
        assert "adb devices" in report
        assert "mitmdump --version" in report
        assert "node --version" in report

    def test_all_report_includes_actions_section(self):
        report = build_report("all")
        assert "【开盘啦占位配置】" in report
        assert "【开盘啦首轮验证清单】" in report
        assert "【开盘啦下一步动作】" in report

    def test_actions_only_section(self):
        report = build_report("actions")
        assert "【开盘啦下一步动作】" in report
        assert "【开盘啦占位配置】" not in report
        assert "【开盘啦首轮验证清单】" not in report

    def test_env_only_section(self):
        report = build_report("env")
        assert "【Mac mini 环境自检】" in report
        assert "【开盘啦占位配置】" not in report
        assert "【开盘啦首轮验证清单】" not in report

    def test_manifest_reflects_known_fields(self):
        report = build_report("manifest")
        assert "包名: com.aiyu.kaipanla" in report
        assert "启动 Activity: .splash.SplashActivity" in report

    def test_environment_check_reports_status(self, monkeypatch):
        def fake_which(command):
            return f"/opt/homebrew/bin/{command}"

        def fake_run(cmd, capture_output, text, timeout):
            if cmd[:2] == ["adb", "devices"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout="List of devices attached\nserial123\tdevice\n",
                    stderr="",
                )
            versions = {
                "git": "git version 2.42.0",
                "python3": "Python 3.11.15",
                "node": "v20.12.2",
                "adb": "Android Debug Bridge version 1.0.41",
                "mitmdump": "Mitmproxy: 11.0.2",
            }
            return SimpleNamespace(
                returncode=0,
                stdout=versions.get(cmd[0], ""),
                stderr="",
            )

        monkeypatch.setattr("src.apps.kaipanla.entry.shutil.which", fake_which)
        monkeypatch.setattr("src.apps.kaipanla.entry.subprocess.run", fake_run)
        monkeypatch.setattr("src.apps.kaipanla.entry.importlib.util.find_spec", lambda name: object())

        report = render_environment_check()
        assert "整体状态: 就绪" in report
        assert "git: OK" in report
        assert "adb devices: OK" in report
        assert "uiautomator2: OK" in report

    def test_environment_check_reports_missing_device(self, monkeypatch):
        def fake_which(command):
            return f"/opt/homebrew/bin/{command}"

        def fake_run(cmd, capture_output, text, timeout):
            if cmd[:2] == ["adb", "devices"]:
                return SimpleNamespace(
                    returncode=0,
                    stdout="List of devices attached\n\n",
                    stderr="",
                )
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr("src.apps.kaipanla.entry.shutil.which", fake_which)
        monkeypatch.setattr("src.apps.kaipanla.entry.subprocess.run", fake_run)
        monkeypatch.setattr("src.apps.kaipanla.entry.importlib.util.find_spec", lambda name: object())

        report = render_environment_check()
        assert "整体状态: 未就绪" in report
        assert "adb devices: FAIL" in report

    def test_capture_command_dispatches_to_runner(self, monkeypatch, capsys):
        captured = {}

        def fake_run_task(task):
            captured["task"] = task
            return SimpleNamespace(
                status="success",
                captured_count=2,
                parsed_count=11,
                report_path="reports/demo.md",
                error="",
                next_action="继续抓行情页其他标签",
                started_at="2026-03-31T16:00:00",
                finished_at="2026-03-31T16:01:00",
                duration_sec=60.0,
                db_path="data/kaipanla.db",
                raw_paths=["data/raw/20260331.jsonl"],
                source_counts={"market_sentiment": 11},
                note_type_counts={"market_emotion_summary": 1},
            )

        monkeypatch.setattr("src.apps.kaipanla.entry.run_task", fake_run_task)

        code = main(["capture"])
        out = capsys.readouterr().out

        assert code == 0
        assert isinstance(captured["task"], TaskSpec)
        assert captured["task"].page == "market_emotion"
        assert "任务:" in out
        assert "# " in out
