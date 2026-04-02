from pathlib import Path
from types import SimpleNamespace

from src.apps.kaipanla.runner import KaipanlaRunner
from src.apps.kaipanla.task import TaskSpec


def test_run_navigation_executes_registered_steps(monkeypatch):
    task = TaskSpec.for_preset("market_radar")
    runner = KaipanlaRunner(task)

    class DummyDevice:
        def __init__(self):
            self.actions = []

        def press(self, key):
            self.actions.append(("press", key))

        def window_size(self):
            return (1000, 2000)

        def swipe(self, *args, **kwargs):
            self.actions.append(("swipe", args))

    dummy = DummyDevice()
    monkeypatch.setattr(KaipanlaRunner, "device", property(lambda self: dummy))
    monkeypatch.setattr(KaipanlaRunner, "_click_text", staticmethod(lambda d, text, timeout=2.0: True))

    result = SimpleNamespace(step_events=[])
    runner._run_task(result)

    event_names = [event["name"] for event in result.step_events]
    assert "tap_radar_tab" in event_names
    assert any(action[0] == "press" for action in dummy.actions)
    assert any(action[0] == "swipe" for action in dummy.actions)


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
