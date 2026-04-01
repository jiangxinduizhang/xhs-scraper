from pathlib import Path

from src.apps.kaipanla.runner import KaipanlaRunner
from src.apps.kaipanla.task import TaskSpec


def test_archive_previous_artifacts(tmp_path):
    task = TaskSpec.market_emotion_default()
    task.runs_dir = str(tmp_path / "runs")
    task.reports_dir = str(tmp_path / "reports")

    task_path = Path(task.runs_dir) / f"{task.task_id}.task.json"
    run_path = Path(task.runs_dir) / f"{task.task_id}.json"
    report_path = Path(task.reports_dir) / f"{task.task_id}.md"

    task_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text("old-task", encoding="utf-8")
    run_path.write_text("old-run", encoding="utf-8")
    report_path.write_text("old-report", encoding="utf-8")

    runner = KaipanlaRunner(task)
    runner._archive_previous_artifacts()

    archive_root = Path(task.runs_dir) / "archive" / task.task_id
    archived = list(archive_root.rglob("*"))
    assert any(path.name == f"{task.task_id}.task.json" for path in archived)
    assert any(path.name == f"{task.task_id}.json" for path in archived)
    assert any(path.name == f"{task.task_id}.md" for path in archived)
    assert not task_path.exists()
    assert not run_path.exists()
    assert not report_path.exists()
