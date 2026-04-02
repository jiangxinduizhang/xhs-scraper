from src.apps.kaipanla.exploration import build_exploration_result
from src.apps.kaipanla.task import RunResult


def test_exploration_detector_prioritizes_target_keys(tmp_path):
    raw_path = tmp_path / "20260402.jsonl"
    raw_path.write_text(
        '\n'.join([
            '{"path":"/w1/api/index.php","data":{"LongHuBang":[{"Name":"联环药业"}],"DragonTigerList":[{"Code":"600513"}],"List":[1],"Day":"2026-04-02","Time":1775097000}}',
            '{"path":"/w1/api/index.php","data":{"DaBanList":{"ZHQD":31},"CWeatherVaneList":[],"MsgTop":[],"TCop":[],"Day":"2026-04-02","Time":1775097001}}',
        ]) + '\n',
        encoding="utf-8",
    )

    run = RunResult(
        task_id="kpl-dragon-tiger-test",
        status="success",
        raw_paths=[str(raw_path)],
        step_events=[
            {"name": "home_reached"},
            {"name": "market_reached"},
            {"name": "dragon_tiger_reached"},
        ],
        captured_count=2,
        parsed_count=10,
    )

    result = build_exploration_result("kpl-dragon-tiger-test", run, "探索抓取今天龙虎榜")

    assert result.status in {"candidate_found", "ready_to_promote"}
    assert "LongHuBang" in result.candidate_keys[:3]
    assert result.recommended_page_name == "dragon_tiger"
    assert result.evidence["target_profile"] == "dragon_tiger"
    assert result.evidence["readiness_score"] >= 5


def test_exploration_detector_marks_noise_keys(tmp_path):
    raw_path = tmp_path / "20260402.jsonl"
    raw_path.write_text(
        '{"path":"/w1/api/index.php","data":{"errcode":0,"t":1,"MsgTop":[],"TCop":[],"IndexAd":[],"ViewTop":[],"Day":"2026-04-02"}}\n',
        encoding="utf-8",
    )

    run = RunResult(
        task_id="kpl-noise-test",
        status="success",
        raw_paths=[str(raw_path)],
        step_events=[{"name": "market_reached"}],
        captured_count=1,
        parsed_count=1,
    )

    result = build_exploration_result("kpl-noise-test", run, "探索抓取今天龙虎榜")

    assert "errcode" in result.likely_noise_keys
    assert "t" in result.likely_noise_keys
    assert result.status == "not_ready"
