"""Fixtures for the frozen joint-identifiability protocol, one refusal per rule.

Every check here has a partner that must fail, because the failure mode this protocol exists
to stop is a verdict that looks orderly: one visible candidate promoted to IDENTIFIED, an
inconsistent record folded into "insufficient evidence", or a candidate chosen because its
number matches the paper.

    python -m pytest tests/test_joint_identifiability.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("ji", REPO / "tools" / "joint_identifiability.py")
ji = importlib.util.module_from_spec(_SPEC)
sys.modules["ji"] = ji
_SPEC.loader.exec_module(ji)


def verdict(**over):
    base = {
        "decision_id": "CMP-001/D1",
        "study_id": "S1",
        "state": "IDENTIFIED",
        "admissible_tuples": 1,
        "compatibility_constraints_applied": True,
        "unknown_tuples": 0,
        "unevaluated_tuples": 0,
        "universe_closure": "IMMUTABLE_INDEX",
        "components": {c: {"candidates": ["c1"], "evidence": "release tag with asset digests",
                           "binding": "UNBOUND"} for c in ji.COMPONENTS},
    }
    base.update(over)
    return base


def test_closed_compatible_singleton_can_supply_effective_joint_binding():
    ji.check(verdict())


def test_one_visible_candidate_without_a_closed_universe_is_not_identified():
    with pytest.raises(ji.ProtocolViolation, match="closure ground"):
        ji.check(verdict(universe_closure=None))


def test_open_universe_singleton_is_admitted_for_the_same_evidence():
    ji.check(verdict(state="OPEN_UNIVERSE_SINGLETON", universe_closure=None))


def test_a_closed_universe_singleton_may_not_be_downgraded():
    with pytest.raises(ji.ProtocolViolation, match="is IDENTIFIED"):
        ji.check(verdict(state="OPEN_UNIVERSE_SINGLETON"))


def test_selecting_a_candidate_because_it_matches_the_reported_number_is_refused():
    components = {c: {"candidates": ["c1"], "evidence": "release tag", "binding": "UNBOUND"}
                  for c in ji.COMPONENTS}
    components["run_output_set"]["evidence"] = "chose the archive that matches_reported 19.0%"
    with pytest.raises(ji.ProtocolViolation, match="prohibited"):
        ji.check(verdict(components=components))


def test_recomputation_evidence_is_refused_even_when_it_would_confirm():
    components = {c: {"candidates": ["c1"], "evidence": "manifest", "binding": "UNBOUND"}
                  for c in ji.COMPONENTS}
    components["release_set"]["evidence"] = "our recomputation reproduces this release exactly"
    with pytest.raises(ji.ProtocolViolation, match="prohibited"):
        ji.check(verdict(components=components))


def test_no_admissible_tuple_is_not_unidentified():
    # Every component enumerable, no compatible combination: the states are kept apart.
    with pytest.raises(ji.ProtocolViolation, match="NO_ADMISSIBLE_TUPLE"):
        ji.check(verdict(state="UNIDENTIFIED", admissible_tuples=0, universe_closure=None))


def test_no_admissible_tuple_requires_a_diagnosis():
    with pytest.raises(ji.ProtocolViolation, match="diagnosis"):
        ji.check(verdict(state="NO_ADMISSIBLE_TUPLE", admissible_tuples=0,
                         universe_closure=None))


def test_no_admissible_tuple_admits_multiple_causes_and_unresolved():
    ji.check(verdict(state="NO_ADMISSIBLE_TUPLE", admissible_tuples=0, universe_closure=None,
                     diagnosis=["EVIDENCE_CONTRADICTS", "UNRESOLVED"],
                     compatibility_constraints_applied=True, unknown_tuples=0,
                     unevaluated_tuples=0))


def test_evaluated_compatibility_with_unknown_tuples_stays_unresolved():
    ji.check(verdict(state="COMPATIBILITY_NOT_EVALUATED", admissible_tuples=0,
                     universe_closure=None, compatibility_constraints_applied=True,
                     unknown_tuples=2, unevaluated_tuples=0))


def test_complete_compatibility_cannot_stay_not_evaluated():
    with pytest.raises(ji.ProtocolViolation, match="no UNKNOWN or unevaluated tuples"):
        ji.check(verdict(state="COMPATIBILITY_NOT_EVALUATED", admissible_tuples=0,
                         universe_closure=None, compatibility_constraints_applied=True,
                         unknown_tuples=0, unevaluated_tuples=0))


def test_terminal_compatibility_state_requires_a_complete_filter():
    with pytest.raises(ji.ProtocolViolation, match="complete compatibility evaluation"):
        ji.check(verdict(state="NO_ADMISSIBLE_TUPLE", admissible_tuples=0,
                         universe_closure=None,
                         compatibility_constraints_applied=False,
                         diagnosis=["EVIDENCE_CONTRADICTS"]))


def test_unidentified_requires_an_unenumerable_component():
    components = {c: {"candidates": ["c1"], "binding": "UNBOUND"} for c in ji.COMPONENTS}
    components["evaluator_and_configuration"] = {"candidates": [], "binding": "UNBOUND"}
    ji.check(verdict(state="UNIDENTIFIED", admissible_tuples=None, universe_closure=None,
                     compatibility_constraints_applied=False, unknown_tuples=None,
                     unevaluated_tuples=None, components=components))


def test_unidentified_must_not_encode_unrun_compatibility_as_zero():
    components = {c: {"candidates": ["c1"], "binding": "UNBOUND"} for c in ji.COMPONENTS}
    components["evaluator_and_configuration"] = {"candidates": [], "binding": "UNBOUND"}
    with pytest.raises(ji.ProtocolViolation, match="must be null"):
        ji.check(verdict(state="UNIDENTIFIED", admissible_tuples=0, universe_closure=None,
                         components=components))


def test_ambiguous_must_record_the_value_range_it_leaves_open():
    with pytest.raises(ji.ProtocolViolation, match="implied_value_range"):
        ji.check(verdict(state="AMBIGUOUS", admissible_tuples=3, universe_closure=None))


def test_a_component_with_no_candidates_cannot_support_a_stronger_state():
    components = {c: {"candidates": ["c1"], "binding": "UNBOUND"} for c in ji.COMPONENTS}
    components["task_universe"] = {"candidates": [], "binding": "UNBOUND"}
    with pytest.raises(ji.ProtocolViolation, match="more than enumerability"):
        ji.check(verdict(components=components))


def test_missing_components_are_refused_rather_than_defaulted():
    components = {c: {"candidates": ["c1"], "binding": "UNBOUND"}
                  for c in ji.COMPONENTS if c != "aggregation_rule"}
    with pytest.raises(ji.ProtocolViolation, match="components not recorded"):
        ji.check(verdict(components=components))


def test_component_binding_is_required_and_enumerated():
    components = verdict()["components"]
    del components["task_universe"]["binding"]
    with pytest.raises(ji.ProtocolViolation, match="binding must be one of"):
        ji.check(verdict(components=components))


def test_not_applicable_evaluator_is_limited_to_direct_outcomes():
    components = verdict()["components"]
    components["evaluator_and_configuration"]["candidates"] = [
        "NOT_APPLICABLE:MACHINE_RESOLUTION_RATE"
    ]
    with pytest.raises(ji.ProtocolViolation, match="NOT_APPLICABLE candidate is invalid"):
        ji.check(verdict(outcome_profile="MACHINE_RESOLUTION_RATE", components=components))


def test_direct_outcome_requires_the_single_not_applicable_evaluator():
    with pytest.raises(ji.ProtocolViolation, match="direct outcome requires"):
        ji.check(verdict(outcome_profile="EMPTY_PATCH_RATE"))


def test_study_is_identified_only_when_every_decision_is():
    mixed = [{"study_id": "S1", "state": "IDENTIFIED"},
             {"study_id": "S1", "state": "OPEN_UNIVERSE_SINGLETON"},
             {"study_id": "S2", "state": "IDENTIFIED"}]
    assert ji.aggregate(mixed) == {"S1": "NOT_IDENTIFIED", "S2": "IDENTIFIED"}


def test_condition_groups_and_studies_are_aggregated_separately():
    rows = [
        {"study_id": "SWEGYM", "condition_group": "OPENHANDS", "state": "IDENTIFIED"},
        {"study_id": "SWEGYM", "condition_group": "MOATLESS", "state": "UNIDENTIFIED"},
    ]

    assert ji.aggregate(rows, "condition_group") == {
        "OPENHANDS": "IDENTIFIED", "MOATLESS": "NOT_IDENTIFIED"
    }
    assert ji.aggregate(rows, "study_id") == {"SWEGYM": "NOT_IDENTIFIED"}


def test_protocol_digest_is_the_file_that_is_frozen():
    assert len(ji.protocol_digest()) == 64
    assert ji.PROTOCOL.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
