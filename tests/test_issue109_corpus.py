"""Check the frozen synthetic Issue 109 comparison examples for internal consistency."""

import json
import tomllib
from pathlib import Path

CORPUS = Path(__file__).parent / "fixtures" / "issue109" / "tasks.json"


def test_issue109_corpus_expected_results_match_inputs() -> None:
    tasks = json.loads(CORPUS.read_text(encoding="utf-8"))["tasks"]
    assert [task["id"] for task in tasks] == ["drift", "path", "extra"]

    drift, path, extra = tasks
    registrations = tomllib.loads(drift["input_files"][".codex/config.toml"])["agents"]
    observed = []
    for name, pin in drift["pins"].items():
        role_path = ".codex/" + registrations[name]["config_file"]
        role = tomllib.loads(drift["input_files"][role_path])
        for field, expected in pin.items():
            if role[field] != expected:
                observed.append(
                    {"path": role_path, "field": field, "expected": expected, "actual": role[field]}
                )
    assert observed == drift["expected"]["findings"]

    original = path["input_files"][".codex/config.toml"]
    corrected = path["expected"]["corrected_files"][".codex/config.toml"]
    assert (
        original.replace('"agents/bounded-worker.tom"', '"agents/bounded-worker.toml"') == corrected
    )
    original_config = tomllib.loads(original)
    assert (
        ".codex/" + original_config["agents"]["bounded_worker"]["config_file"]
        not in path["input_files"]
    )
    config = tomllib.loads(corrected)
    assert ".codex/" + config["agents"]["bounded_worker"]["config_file"] in path["input_files"]

    registrations = tomllib.loads(extra["input_files"][".codex/config.toml"])["agents"]
    unexpected = sorted(set(registrations) - set(extra["inventory"]))
    assert [{"kind": "extra_registration", "name": name} for name in unexpected] == extra[
        "expected"
    ]["findings"]
