from src.apps.kaipanla.task import RunResult, TaskSpec
from src.apps.kaipanla.verify import render_verification_summary, verify_run
from src.proxy.parser import NoteItem
from src.storage.db import Database


def test_verify_run_success(tmp_path):
    db_path = tmp_path / "kaipanla.db"
    task = TaskSpec.market_emotion_default()
    task.db_path = str(db_path)
    task.runs_dir = str(tmp_path / "runs")
    task.reports_dir = str(tmp_path / "reports")
    task.raw_dir = str(tmp_path / "raw")

    task_path = tmp_path / "runs" / f"{task.task_id}.task.json"
    run_path = tmp_path / "runs" / f"{task.task_id}.json"
    report_path = tmp_path / "reports" / f"{task.task_id}.md"
    raw_path = tmp_path / "raw" / "20260331.jsonl"

    task.save(task_path)

    db = Database(str(db_path))
    db.save([
        NoteItem(
            note_id="market:summary:2026-03-31",
            title="市场情绪总览",
            desc="综合强度35",
            author_id="DaBanList",
            author_name="开盘啦",
            liked_count=35,
            collected_count=53,
            comment_count=1,
            cover_url="",
            note_type="market_emotion_summary",
            source="market_sentiment",
        )
    ])

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"path":"/w1/api/index.php","data":{"BaceFaceList":[]}}\\n', encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("report", encoding="utf-8")

    result = RunResult(
        task_id=task.task_id,
        status="success",
        raw_paths=[str(raw_path)],
        db_path=str(db_path),
        report_path=str(report_path),
        step_events=[
            {"name": "launch_app", "detail": "com.aiyu.kaipanla", "at": "2026-03-31T16:00:00"},
            {"name": "home_reached", "detail": "首页", "at": "2026-03-31T16:00:01"},
            {"name": "market_reached", "detail": "行情", "at": "2026-03-31T16:00:02"},
            {"name": "emotion_reached", "detail": "情绪", "at": "2026-03-31T16:00:03"},
            {"name": "request_captured", "detail": "5", "at": "2026-03-31T16:00:10"},
            {"name": "report_written", "detail": str(report_path), "at": "2026-03-31T16:00:11"},
            {"name": "run_written", "detail": str(run_path), "at": "2026-03-31T16:00:12"},
        ],
    )
    result.save(run_path)

    verification = verify_run(run_path)

    assert verification.status == "verified"
    assert "report.md 已生成" in verification.checks
    assert any("market_sentiment 记录数" in item for item in verification.details)
    assert "步骤时间线完整" in verification.details


def test_render_verification_summary():
    summary = render_verification_summary(
        verify_run("missing.json")
    )
    assert "状态: missing" in summary
