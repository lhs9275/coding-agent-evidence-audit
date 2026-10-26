"""Fixtures for the relaxation ladder, including its own positive control.

A ladder that reports "no rung identifies anything" is only informative if some input would
make it say otherwise. These checks feed it records that must climb: one that is identifiable
outright, and one that becomes identifiable exactly when the closure requirement is dropped.
Without them the all-negative ladder would be indistinguishable from a ladder that cannot say
yes at all.

    python -m pytest tests/test_sensitivity_ladder.py
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("sl", REPO / "tools" / "sensitivity_ladder.py")
sl = importlib.util.module_from_spec(_SPEC)
sys.modules["sl"] = sl
_SPEC.loader.exec_module(sl)

RUNGS = {name: (components, unique, closure) for name, components, unique, closure, _ in sl.LADDER}


def record(counts: dict[str, int], closure: str | None = None,
           state: str | None = None, admissible: int | None = 1,
           compatibility: bool = True) -> dict:
    return {"universe_closure": closure,
            "state": state or ("IDENTIFIED" if closure else "OPEN_UNIVERSE_SINGLETON"),
            "admissible_tuples": admissible,
            "compatibility_constraints_applied": compatibility,
            "components": {name: {"candidates": [f"c{i}" for i in range(counts.get(name, 1))]}
                           for name in sl.ALL_COMPONENTS}}


def at(rung: str, verdict: dict) -> str:
    components, unique, closure = RUNGS[rung]
    return sl.evaluate(verdict, components, unique, closure)


def test_a_unique_closed_record_is_identified_at_the_strictest_rung():
    assert at("R0", record({}, closure="IMMUTABLE_INDEX")) == "IDENTIFIED"


def test_an_unfiltered_singleton_is_not_promoted_to_identified():
    unfiltered = record({}, closure="IMMUTABLE_INDEX",
                        state="COMPATIBILITY_NOT_EVALUATED", admissible=None,
                        compatibility=False)
    assert at("R0", unfiltered) == "COMPATIBILITY_NOT_EVALUATED"


def test_strict_rung_respects_a_filtered_singleton_despite_multiple_raw_candidates():
    identified = record({"release_set": 2}, closure="IMMUTABLE_INDEX",
                        state="IDENTIFIED")
    assert at("R0", identified) == "IDENTIFIED"


def test_strict_rung_preserves_zero_admissible_state():
    none = record({}, closure="IMMUTABLE_INDEX", state="NO_ADMISSIBLE_TUPLE",
                  admissible=0)
    assert at("R0", none) == "NO_ADMISSIBLE_TUPLE"
    assert at("R1", none) == "NO_ADMISSIBLE_TUPLE"


def test_a_unique_record_without_closure_is_held_back_until_the_closure_rung():
    unique_open = record({})
    assert at("R0", unique_open) == "OPEN_UNIVERSE_SINGLETON"
    assert at("R1", unique_open) == "IDENTIFIED"


def test_relaxing_a_requirement_can_rescue_a_record_that_only_failed_on_it():
    # Everything unique except the aggregation rule, which has two candidates.
    verdict = record({"aggregation_rule": 2}, state="AMBIGUOUS", admissible=2)
    assert at("R1", verdict) == "AMBIGUOUS"
    assert at("R2", verdict) == "COMPATIBILITY_NOT_EVALUATED"


def test_a_missing_component_is_unidentified_however_far_the_rung_relaxes():
    verdict = record({"run_output_set": 0}, state="UNIDENTIFIED", admissible=None,
                     compatibility=False)
    for rung in RUNGS:
        assert at(rung, verdict) == "UNIDENTIFIED", rung


def test_dropping_a_component_stops_its_absence_from_mattering():
    verdict = record({"aggregation_rule": 0}, state="UNIDENTIFIED", admissible=None,
                     compatibility=False)
    assert at("R1", verdict) == "UNIDENTIFIED"
    assert at("R2", verdict) == "COMPATIBILITY_NOT_EVALUATED"


def test_the_availability_rung_ignores_uniqueness_but_not_absence():
    assert at("R5", record({"release_set": 9, "run_output_set": 9})) == "AVAILABLE"
    assert at("R5", record({"release_set": 0})) == "UNIDENTIFIED"


def test_no_case_requires_a_component_outside_the_protocol_tuple():
    # R5 restores the full tuple as a separate availability comparator.
    for name, components, _, _, _ in sl.LADDER:
        assert set(components) <= set(sl.ALL_COMPONENTS), name


def test_generator_refuses_a_protocol_invalid_verdict_payload(tmp_path):
    components = {name: {"candidates": ["c1"], "binding": "UNBOUND"}
                  for name in sl.ALL_COMPONENTS}
    payload = {"protocol_sha256": hashlib.sha256(sl.PROTOCOL.read_bytes()).hexdigest(),
               "verdicts": [
                   {"decision_id": decision, "state": "UNIDENTIFIED",
                    "components": components, "admissible_tuples": None,
                    "unknown_tuples": None, "unevaluated_tuples": None,
                    "compatibility_constraints_applied": False}
                   for decision in sorted(sl.EXPECTED_DECISIONS)
               ]}
    source, output = tmp_path / "invalid.json", tmp_path / "out.json"
    source.write_text(json.dumps(payload))

    with pytest.raises(Exception, match="UNIDENTIFIED requires"):
        sl.main(["--verdicts", str(source), "--out", str(output)])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
