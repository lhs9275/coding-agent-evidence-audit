"""Fixtures for the ledger crosswalk, including the collapses it must refuse.

The crosswalk's whole value is that it distinguishes four things a careless table would merge:
a component the ledger settled, one it half settled, one it asked about and did not settle,
and one it never asked about. Each is checked here against an input that must not produce it.

    python -m pytest tests/test_crosswalk_ledger.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("cw", REPO / "tools" / "crosswalk_ledger.py")
cw = importlib.util.module_from_spec(_SPEC)
sys.modules["cw"] = cw
_SPEC.loader.exec_module(cw)


def cell(*items):
    return {"comparison_id": "CMP-X", "condition_group": "G", "items": list(items)}


def item(kind_states, **over):
    base = {"kind_states": kind_states, "recorded_immutable_digest": None,
            "digest_scope_matches": False}
    base.update(over)
    return base


def test_every_required_kind_available_is_determined():
    assert cw.coverage({"TASK_MEMBERSHIP": "AVAILABLE", "SELECTION_CANDIDATES": "AVAILABLE"},
                       cw.MAPPING["task_universe"]) == "DETERMINED"


def test_one_unavailable_kind_downgrades_to_partial():
    assert cw.coverage({"TASK_MEMBERSHIP": "AVAILABLE", "SELECTION_CANDIDATES": "INCOMPLETE"},
                       cw.MAPPING["task_universe"]) == "PARTIAL"


def test_no_kind_available_is_not_reached_not_partial():
    assert cw.coverage({"TASK_MEMBERSHIP": "ABSENT_ATTEMPTED"},
                       cw.MAPPING["task_universe"]) == "NOT_REACHED"


def test_a_component_the_ledger_never_asked_about_is_not_an_absence():
    # The distinction the table exists for: no question asked is not an answer of absent.
    assert cw.coverage({}, cw.MAPPING["evaluator_and_configuration"]) == "NOT_REQUIRED_BY_LEDGER"
    assert cw.coverage({"SOMETHING_ELSE": "AVAILABLE"},
                       cw.MAPPING["evaluator_and_configuration"]) == "NOT_REQUIRED_BY_LEDGER"


def test_worst_state_wins_across_items_in_one_decision():
    row = cw.crosswalk(cell(item({"TASK_MEMBERSHIP": "AVAILABLE"}),
                            item({"TASK_MEMBERSHIP": "ABSENT_ATTEMPTED"})))
    assert row["kind_states"]["TASK_MEMBERSHIP"] == "ABSENT_ATTEMPTED"
    assert row["components"]["task_universe"] == "NOT_REACHED"


def test_a_scope_matched_immutable_digest_lifts_release_set_but_not_to_determined():
    row = cw.crosswalk(cell(item({"ENVIRONMENT_IDENTITY": "ABSENT_ATTEMPTED"},
                                 recorded_immutable_digest="sha256:abc",
                                 digest_scope_matches=True)))
    assert row["components"]["release_set"] == "PARTIAL"


def test_a_digest_whose_scope_does_not_match_lifts_nothing():
    row = cw.crosswalk(cell(item({"ENVIRONMENT_IDENTITY": "ABSENT_ATTEMPTED"},
                                 recorded_immutable_digest="sha256:abc",
                                 digest_scope_matches=False)))
    assert row["components"]["release_set"] == "NOT_REACHED"


def test_resource_clock_maps_to_no_component():
    mapped = {kind for kinds in cw.MAPPING.values() for kind in kinds}
    assert "RESOURCE_CLOCK" not in mapped
    assert "RESOURCE_CLOCK" in cw.UNMAPPED


def test_outcome_records_map_to_run_outputs_not_rule_or_evaluator_metadata():
    assert "EVALUATOR_OUTCOME" in cw.MAPPING["run_output_set"]
    assert "HUMAN_LABEL" in cw.MAPPING["run_output_set"]
    assert "EVALUATOR_OUTCOME" not in cw.MAPPING["evaluator_and_configuration"]
    assert "HUMAN_LABEL" not in cw.MAPPING["aggregation_rule"]


def test_missingness_is_an_aggregation_rule_not_task_membership():
    assert "TERMINAL_MISSINGNESS" in cw.MAPPING["aggregation_rule"]
    assert "TERMINAL_MISSINGNESS" not in cw.MAPPING["task_universe"]


def test_needs_reread_lists_every_component_short_of_determined():
    row = cw.crosswalk(cell(item({"TASK_MEMBERSHIP": "AVAILABLE",
                                  "SELECTION_CANDIDATES": "AVAILABLE",
                                  "TERMINAL_MISSINGNESS": "AVAILABLE"})))
    assert "task_universe" not in row["needs_artifact_reread"]
    assert "release_set" in row["needs_artifact_reread"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
