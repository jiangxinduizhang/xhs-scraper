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

    assert result.evidence_status == "evidence_complete"
    assert "LongHuBang" in result.observed_keys[:5]
    assert "/w1/api/index.php" in result.observed_paths
    assert any(item["name"] == "LongHuBang" for item in result.evidence["structure_facts"]["candidate_structures"])


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

    assert "errcode" in result.evidence["structure_facts"]["noise_keys"]
    assert "t" in result.evidence["structure_facts"]["noise_keys"]
    assert result.evidence_status == "evidence_complete"


def test_exploration_records_generic_list_case_as_facts(tmp_path):
    raw_path = tmp_path / "20260402.jsonl"
    raw_path.write_text(
        '\n'.join([
            '{"path":"/w1/api/index.php","data":{"List":[1,2,3],"Day":"2026-04-02","Time":1775097000}}',
            '{"path":"/w1/api/index.php","data":{"DaBanList":{"ZHQD":31},"MsgTop":[],"TCop":[],"Day":"2026-04-02","Time":1775097001}}',
        ]) + '\n',
        encoding="utf-8",
    )

    run = RunResult(
        task_id="kpl-generic-list-test",
        status="success",
        raw_paths=[str(raw_path)],
        step_events=[
            {"name": "home_reached"},
            {"name": "market_reached"},
            {"name": "dragon_tiger_reached"},
        ],
        captured_count=2,
        parsed_count=3,
    )

    result = build_exploration_result("kpl-generic-list-test", run, "探索抓取今天龙虎榜")

    assert result.evidence_status == "evidence_complete"
    assert "List" in result.observed_keys
    assert "DaBanList" in result.observed_keys
    assert any(item["name"] == "List" for item in result.evidence["structure_facts"]["candidate_structures"])


def test_exploration_evidence_includes_timing_and_shape(tmp_path):
    raw_path = tmp_path / "20260402.jsonl"
    raw_path.write_text(
        '{"path":"/w1/api/index.php","data":{"LongHuBang":[{"Name":"联环药业"}],"Day":"2026-04-02","Time":1775097000}}\n',
        encoding="utf-8",
    )

    run = RunResult(
        task_id="kpl-evidence-shape-test",
        status="success",
        raw_paths=[str(raw_path)],
        step_events=[
            {"name": "market_reached"},
            {"name": "dragon_tiger_reached"},
        ],
        captured_count=1,
        parsed_count=1,
    )

    result = build_exploration_result("kpl-evidence-shape-test", run, "探索抓取今天龙虎榜")
    structure = next(item for item in result.evidence["structure_facts"]["candidate_structures"] if item["name"] == "LongHuBang")

    assert structure["post_navigation_hits"] >= 1
    assert structure["shape"]["kind"] == "list"
    assert "action_facts" in result.evidence
    assert "request_facts" in result.evidence
    assert "structure_facts" in result.evidence
