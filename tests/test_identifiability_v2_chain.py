from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs" / "paper-a"
_SPEC = importlib.util.spec_from_file_location("ji_chain", REPO / "tools/joint_identifiability.py")
ji = importlib.util.module_from_spec(_SPEC)
sys.modules["ji_chain"] = ji
_SPEC.loader.exec_module(ji)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((DOCS / name).read_text())


def test_checked_in_v2_chain_is_internally_pinned_and_consistent():
    protocol = DOCS / "joint-identifiability-protocol-v2.md"
    candidates_path = DOCS / "component-candidates-v2.json"
    crosswalk_path = DOCS / "identifiability-crosswalk-v2.json"
    verdicts_path = DOCS / "identifiability-verdicts-v2.json"
    candidates, crosswalk, verdicts = map(load, (
        candidates_path.name, crosswalk_path.name, verdicts_path.name,
    ))
    protocol_sha = sha(protocol)
    assert candidates["protocol_sha256"] == crosswalk["protocol_sha256"] == \
        verdicts["protocol_sha256"] == protocol_sha
    assert crosswalk["findings_sha256"] == sha(DOCS / "availability-item-findings-v1.json")
    assert verdicts["candidates_sha256"] == sha(candidates_path)
    assert verdicts["crosswalk_sha256"] == sha(crosswalk_path)
    for name, digest in candidates["availability_attempt_log_sha256s"].items():
        assert digest == sha(DOCS / name)
    assert all(row["sha256"] == row["retrieval_identity"]["logged_sha256"]
               and row["retrieval_identity"]["matches"] for row in candidates["artifacts"])

    rows = verdicts["verdicts"]
    ids = {row["decision_id"] for row in rows}
    assert len(rows) == len(ids) == 20
    assert verdicts["counts"] == {"UNIDENTIFIED": 20}
    assert len(verdicts["condition_group_level"]) == 5
    assert len(verdicts["study_level"]) == 4
    for row in rows:
        ji.check(row)
        counts = {name: len(component["candidates"])
                  for name, component in row["components"].items()}
        assert row["candidate_counts"] == counts
        assert row["components_without_candidates"] == [name for name, count in counts.items()
                                                           if count == 0]
        assert row["enumerated_candidate_combinations"] == math.prod(counts.values())
        assert row["admissible_tuples"] is None
        assert row["unknown_tuples"] is None
        assert row["unevaluated_tuples"] is None
        assert row["compatibility_evaluation_status"] == \
            "NOT_APPLICABLE_MISSING_COMPONENT"

    by_id = {row["decision_id"]: row for row in rows}
    assert by_id["CMP-034"]["candidate_counts"] == {
        "release_set": 1, "run_output_set": 2, "evaluator_and_configuration": 0,
        "task_universe": 1, "aggregation_rule": 0,
    }
    assert by_id["CMP-035"]["candidate_counts"] == {
        "release_set": 1, "run_output_set": 0, "evaluator_and_configuration": 0,
        "task_universe": 2, "aggregation_rule": 1,
    }
    assert by_id["CMP-041"]["candidate_counts"]["release_set"] == 0

    for name in ("compatibility-filter-v2.json", "sensitivity-ladder-v2.json"):
        derived = load(name)
        assert derived["protocol_sha256"] == protocol_sha
        assert derived["verdicts_sha256"] == sha(verdicts_path)
    sensitivity = load("sensitivity-ladder-v2.json")
    assert {row["rung"]: row["counts"] for row in sensitivity["rungs"]} == {
        "R0": {"UNIDENTIFIED": 20}, "R1": {"UNIDENTIFIED": 20},
        "R2": {"UNIDENTIFIED": 20},
        "R3": {"UNIDENTIFIED": 19, "NOT_UNIQUE": 1},
        "R4": {"UNIDENTIFIED": 17, "NOT_UNIQUE": 3},
        "R5": {"UNIDENTIFIED": 20},
    }
    assert "no projected compatibility filter was run here" in sensitivity["reading_rule"]
    assert "answered elsewhere" not in sensitivity["reading_rule"]

    transition = load("identifiability-transition-v1-to-v2.json")
    assert transition["from_verdicts_sha256"] == sha(DOCS / "identifiability-verdicts-v1.json")
    assert transition["to_verdicts_sha256"] == sha(verdicts_path)
    assert {row["decision_id"] for row in transition["rows"]} == ids
    assert transition["counts"] == {
        "COMPATIBILITY_NOT_EVALUATED->UNIDENTIFIED": 2,
        "UNIDENTIFIED->UNIDENTIFIED": 18,
    }
