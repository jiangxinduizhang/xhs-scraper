import json

from scripts.kpl_tool import main
from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.verify import VerificationResult


def _load_stdout(capsys):
    return json.loads(capsys.readouterr().out)


def test_kpl_tool_capture_emits_json(tmp_path, monkeypatch, capsys):
    task = TaskSpec.market_emotion_default()
    task_path = tmp_path / "task.json"
    task.save(task_path)

    def fake_run_task(task_obj):
        return RunResult(
            task_id=task_obj.task_id,
            status="success",
            captured_count=5,
            parsed_count=35,
            source_counts={"market_sentiment": 27},
            note_type_counts={"market_emotion_summary": 1},
            step_events=[{"name": "launch_app", "at": "2026-03-31T17:16:53"}],
            raw_paths=["data/raw/20260331.jsonl"],
            db_path="data/kaipanla.db",
            report_path="reports/demo.md",
            next_action="",
        )

    monkeypatch.setattr("scripts.kpl_tool.run_task", fake_run_task)

    code = main(["capture", "--task", str(task_path)])
    payload = _load_stdout(capsys)

    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "capture"
    assert payload["task"]["task_id"] == task.task_id
    assert payload["run"]["captured_count"] == 5
    assert "page_summary" in payload


def test_kpl_tool_verify_emits_json(tmp_path, monkeypatch, capsys):
    task = TaskSpec.market_emotion_default()
    task_path = tmp_path / "task.json"
    run_path = tmp_path / "run.json"
    task.save(task_path)

    run = RunResult(
        task_id=task.task_id,
        status="success",
        raw_paths=["data/raw/20260331.jsonl"],
        db_path="data/kaipanla.db",
        report_path="reports/demo.md",
        step_events=[
            {"name": "launch_app", "at": "2026-03-31T17:16:53"},
            {"name": "entered_home_tab", "at": "2026-03-31T17:16:54"},
            {"name": "entered_market_tab", "at": "2026-03-31T17:16:55"},
            {"name": "tap_emotion_tab", "at": "2026-03-31T17:16:56"},
            {"name": "request_captured", "at": "2026-03-31T17:16:57"},
            {"name": "report_written", "at": "2026-03-31T17:16:58"},
            {"name": "run_written", "at": "2026-03-31T17:16:59"},
        ],
    )
    run.save(run_path)

    monkeypatch.setattr(
        "scripts.kpl_tool.verify_run",
        lambda run_arg, task_arg=None: VerificationResult(
            task_id=task.task_id,
            status="artifacts_complete",
            checks=["report.md 已生成"],
            details=["步骤时间线完整"],
        ),
    )

    code = main(["verify", "--run", str(run_path), "--task", str(task_path)])
    payload = _load_stdout(capsys)

    assert code == 0
    assert payload["ok"] is True
    assert payload["command"] == "verify"
    assert payload["verification"]["status"] == "artifacts_complete"


def test_kpl_tool_latest_and_status(tmp_path, monkeypatch, capsys):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    task = TaskSpec.market_emotion_default()
    run_path = runs_dir / f"{task.task_id}.json"
    task_path = runs_dir / f"{task.task_id}.task.json"

    task.save(task_path)
    run = RunResult(
        task_id=task.task_id,
        status="success",
        raw_paths=["data/raw/20260331.jsonl"],
        db_path="data/kaipanla.db",
        report_path="reports/demo.md",
        step_events=[{"name": "launch_app", "at": "2026-03-31T17:16:53"}],
    )
    run.save(run_path)

    monkeypatch.setattr("scripts.kpl_tool._latest_run_path", lambda runs_dir="runs": run_path)
    monkeypatch.setattr(
        "scripts.kpl_tool.verify_run",
        lambda run_arg, task_arg=None: VerificationResult(
            task_id=task.task_id,
            status="artifacts_complete",
            checks=[],
            details=["步骤时间线完整"],
        ),
    )

    code = main(["latest", "--runs-dir", str(runs_dir)])
    latest_payload = _load_stdout(capsys)
    assert code == 0
    assert latest_payload["run_path"] == str(run_path)

    code = main(["status", "--runs-dir", str(runs_dir)])
    status_payload = _load_stdout(capsys)
    assert code == 0
    assert status_payload["ok"] is True
    assert status_payload["verification"]["status"] == "artifacts_complete"


def test_kpl_tool_explore_dry_run(capsys):
    code = main(["explore", "探索抓取龙虎榜"])
    payload = _load_stdout(capsys)

    assert code == 0
    assert payload["command"] == "explore"
    assert payload["task"]["mode"] == "exploration"
    assert payload["execute"] is False
    assert payload["runtime_policy"]["max_rounds"] == 2
    assert payload["runtime_policy"]["ai_must_decide_next_step"] is True


def test_kpl_tool_explore_exec_returns_evidence_bundle(monkeypatch, capsys):
    def fake_run_task(task_obj):
        return RunResult(
            task_id=task_obj.task_id,
            status="success",
            captured_count=1,
            parsed_count=1,
            step_events=[
                {"name": "entered_market_tab", "at": "2026-04-02T12:00:00"},
                {"name": "tap_dragon_tiger_tab", "at": "2026-04-02T12:00:01"},
            ],
        )

    fake_exploration = {
        "task_id": "demo",
        "target_hint": "探索抓取龙虎榜",
        "evidence_status": "evidence_complete",
        "status": "evidence_complete",
        "observed_keys": ["List", "DaBanList"],
        "navigation_events": ["entered_market_tab", "tap_dragon_tiger_tab"],
        "raw_record_count": 1,
        "observed_paths": ["/w1/api/index.php"],
        "evidence": {},
    }

    class FakeExploration:
        evidence = {}
        evidence_status = "evidence_complete"
        status = "evidence_complete"
        observed_keys = ["List", "DaBanList"]
        observed_paths = ["/w1/api/index.php"]
        raw_record_count = 1

        def to_dict(self):
            return fake_exploration

    monkeypatch.setattr("scripts.kpl_tool.run_task", fake_run_task)
    monkeypatch.setattr("scripts.kpl_tool.build_exploration_result", lambda *args, **kwargs: FakeExploration())

    code = main(["explore", "探索抓取龙虎榜", "--execute", "--max-rounds", "2"])
    payload = _load_stdout(capsys)

    assert code == 0
    assert payload["requires_ai_decision"] is True
    assert payload["runtime_stop_reason"] == "evidence_bundle_collected"
    assert len(payload["rounds"]) == 1


def test_kpl_tool_has_no_ask_command():
    try:
        main(["ask", "抓取龙虎榜"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("ask command should not be available")
