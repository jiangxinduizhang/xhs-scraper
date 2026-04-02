from pathlib import Path
from types import SimpleNamespace

from src.apps.kaipanla.report import render_run_report
from src.apps.kaipanla.task import RunResult, TaskSpec


def test_task_spec_roundtrip(tmp_path):
    task = TaskSpec.market_emotion_default()
    task_path = tmp_path / "task.json"
    task.save(task_path)

    loaded = TaskSpec.load(task_path)
    assert loaded.task_id == task.task_id
    assert loaded.page == "market_emotion"
    assert loaded.goal == "采集市场情绪页相关产物"


def test_task_spec_supports_multiple_registered_pages():
    radar = TaskSpec.for_preset("market_radar")
    featured = TaskSpec.for_preset("market_featured")
    dragon = TaskSpec.for_preset("dragon_tiger")

    assert radar.page == "market_radar"
    assert featured.page == "market_featured"
    assert dragon.page == "dragon_tiger"


def test_task_spec_supports_exploration_mode():
    task = TaskSpec.for_exploration("探索抓取龙虎榜")

    assert task.mode == "exploration"
    assert task.target_hint == "探索抓取龙虎榜"
    assert "collect_evidence_bundle" in task.success_criteria
    assert "evidence_bundle" in task.output
    assert "runtime_role: execution_only" in task.notes


def test_run_result_roundtrip(tmp_path):
    result = RunResult(
        task_id="task-001",
        status="success",
        captured_count=3,
        parsed_count=11,
        source_counts={"market_sentiment": 11},
        note_type_counts={"market_emotion_summary": 1},
        step_events=[
            {"name": "launch_app", "detail": "com.aiyu.kaipanla", "at": "2026-03-31T16:00:00"},
            {"name": "entered_home_tab", "detail": "首页", "at": "2026-03-31T16:00:02"},
        ],
        raw_paths=["data/raw/20260331.jsonl"],
        db_path="data/kaipanla.db",
        next_action="",
    )
    run_path = tmp_path / "run.json"
    result.save(run_path)

    loaded = RunResult.load(run_path)
    assert loaded.task_id == "task-001"
    assert loaded.status == "success"
    assert loaded.captured_count == 3
    assert loaded.note_type_counts["market_emotion_summary"] == 1


def test_render_run_report_includes_stats():
    task = TaskSpec.market_emotion_default()
    result = SimpleNamespace(
        status="success",
        started_at="2026-03-31T16:00:00",
        finished_at="2026-03-31T16:01:00",
        duration_sec=60.0,
        captured_count=2,
        parsed_count=11,
        db_path="data/kaipanla.db",
        raw_paths=["data/raw/20260331.jsonl"],
        next_action="",
        source_counts={"market_sentiment": 11},
        note_type_counts={"market_emotion_summary": 1, "market_baceface": 4},
        step_events=[{"name": "launch_app", "detail": "com.aiyu.kaipanla", "at": "2026-03-31T16:00:00"}],
        error="",
        report_path="reports/demo.md",
    )

    report = render_run_report(task, result)
    assert task.task_id in report
    assert "状态: success" in report
    assert "market_sentiment: 11" in report
    assert "market_emotion_summary: 1" in report
    assert "本报告展示的是执行与产物事实" in report
    assert "步骤时间线" in report
