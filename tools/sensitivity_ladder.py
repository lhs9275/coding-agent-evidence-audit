"""Relax the identifiability criterion and report what changes.

The all-negative result invites one obvious objection: that the zero is a property of a rule
we chose rather than of the records we read. This answers it by weakening the rule through
R0--R4 and then applying a separate availability-only comparator at R5, so a reader can see
which requirement is load-bearing and whether any case identifies a decision.

The analysis is declared here before it is run; no case adds evidence or consults a reported
value. R5 is not a continuation of R4: it restores all components and drops uniqueness to
restate the earlier component-wise availability question. The analysis is post hoc: it was
written after the all-negative result was known, and saying otherwise would be the kind of
claim this project has already had to withdraw once.

    R0  the criterion as adjudicated: five components, joint uniqueness, closed universe
    R1  drop the candidate-universe closure requirement
    R2  R1, and stop requiring an aggregation rule
    R3  R2, and stop requiring an evaluator and configuration
    R4  R3, and stop requiring a release set
    R5  separate availability comparator: all components need a candidate; uniqueness not required

    python tools/sensitivity_ladder.py --out PATH
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs" / "paper-a"
PROTOCOL = DOCS / "joint-identifiability-protocol-v2.md"

_SPEC = importlib.util.spec_from_file_location(
    "joint_identifiability_for_sensitivity", REPO / "tools" / "joint_identifiability.py"
)
ji = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ji
_SPEC.loader.exec_module(ji)

ALL_COMPONENTS = ("release_set", "run_output_set", "evaluator_and_configuration",
                  "task_universe", "aggregation_rule")
EXPECTED_DECISIONS = {
    "CMP-001", "CMP-002", "CMP-003", "CMP-004", "CMP-006", "CMP-007",
    "CMP-008", "CMP-009", "CMP-010", "CMP-011", "CMP-012", "CMP-013",
    "CMP-018", "CMP-019", "CMP-021", "CMP-022", "CMP-024", "CMP-034",
    "CMP-035", "CMP-041",
}

# Each rung: which components it still requires, whether uniqueness is required, and whether
# a closed candidate universe is required for the strongest verdict.
LADDER = (
    ("R0", ALL_COMPONENTS, True, True,
     "the criterion as adjudicated"),
    ("R1", ALL_COMPONENTS, True, False,
     "closure of the candidate universe no longer required"),
    ("R2", tuple(c for c in ALL_COMPONENTS if c != "aggregation_rule"), True, False,
     "and an aggregation rule no longer required"),
    ("R3", tuple(c for c in ALL_COMPONENTS
                 if c not in ("aggregation_rule", "evaluator_and_configuration")), True, False,
     "and an evaluator and configuration no longer required"),
    ("R4", ("run_output_set", "task_universe"), True, False,
     "and a release set no longer required"),
    ("R5", ALL_COMPONENTS, False, False,
     "separate availability comparator: all components restored, uniqueness not required"),
)


def evaluate(verdict: dict, components: tuple[str, ...], unique: bool, closure: bool) -> str:
    if components == ALL_COMPONENTS and unique and closure and verdict.get("state"):
        return verdict["state"]  # R0 is the adjudicated protocol result, not a recount.
    counts = {name: len(verdict["components"][name]["candidates"]) for name in components}
    if any(n == 0 for n in counts.values()):
        return "UNIDENTIFIED"
    if not unique:
        # R5 asks only whether something was published for each required component, which is
        # the question the earlier component-wise criterion asked.
        return "AVAILABLE"
    if components == ALL_COMPONENTS and verdict.get("state"):
        if verdict["state"] == "OPEN_UNIVERSE_SINGLETON" and not closure:
            return "IDENTIFIED"
        return verdict["state"]
    product = 1
    for n in counts.values():
        product *= n
    if product > 1:
        # Uniqueness fails on the enumerated candidates. Whether any survive the pairwise
        # filter is a separate question this ladder does not re-open.
        return "NOT_UNIQUE"
    if verdict.get("state") == "IDENTIFIED":
        return "IDENTIFIED"
    if verdict.get("state") == "OPEN_UNIVERSE_SINGLETON" and not closure:
        return "IDENTIFIED"
    # Dropping a coordinate can expose a structural singleton, but the original filter did
    # not evaluate that projected tuple. Do not promote it without a new compatibility pass.
    if verdict.get("state") or not verdict.get("compatibility_constraints_applied"):
        return "COMPATIBILITY_NOT_EVALUATED"
    if closure and not verdict.get("universe_closure"):
        return "OPEN_UNIVERSE_SINGLETON"
    return "IDENTIFIED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdicts", type=Path, default=DOCS / "identifiability-verdicts-v2.json")
    parser.add_argument("--out", type=Path, default=DOCS / "sensitivity-ladder-v2.json")
    args = parser.parse_args(argv)

    payload = json.loads(args.verdicts.read_text())
    live_protocol_sha256 = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    if payload.get("protocol_sha256") != live_protocol_sha256:
        raise ValueError("protocol digest mismatch")
    verdicts = payload["verdicts"]
    decision_ids = [verdict["decision_id"] for verdict in verdicts]
    if (len(decision_ids) != 20 or len(set(decision_ids)) != 20
            or set(decision_ids) != EXPECTED_DECISIONS):
        raise ValueError("sensitivity input must contain each exact audited decision once")
    for verdict in verdicts:
        ji.check(verdict)
    rungs = []
    for name, components, unique, closure, description in LADDER:
        states = [evaluate(v, components, unique, closure) for v in verdicts]
        counts = dict(Counter(states))
        rungs.append({"rung": name, "description": description,
                      "requires": list(components), "requires_uniqueness": unique,
                      "requires_closed_universe": closure,
                      "counts": counts,
                      "identified_or_available": counts.get("IDENTIFIED", 0) + counts.get("AVAILABLE", 0),
                      "per_decision": {v["decision_id"]: s for v, s in zip(verdicts, states)}})
        print(f"  {name}  {counts}   <- {description}")

    first_pass = next((r["rung"] for r in rungs if r["counts"].get("IDENTIFIED")), None)
    print(f"\nfirst rung at which any decision is IDENTIFIED: {first_pass or 'none'}")

    args.out.write_text(json.dumps({
        "schema": "sensitivity-ladder.v2", "scientific_claims": True,
        "analysis_timing": "POST_HOC_AFTER_ALL_NEGATIVE_RESULT",
        "protocol_sha256": live_protocol_sha256,
        "verdicts_sha256": hashlib.sha256(args.verdicts.read_bytes()).hexdigest(),
        "reported_values_consulted": False,
        "reading_rule": (
            "R0 through R4 remove requirements cumulatively; R5 is a separate comparator"
            " that restores all components and removes uniqueness. No case supplies evidence"
            " the record does not contain. NOT_UNIQUE means the enumerated candidates do not"
            " single one out, and is not a claim that no combination survives the pairwise"
            " compatibility filter -- no projected compatibility filter was run here."
            " AVAILABLE at R5 is the question the earlier component-wise criterion"
            " asked, included so the two criteria can be compared on the same records."
            " R0 preserves the adjudicated state. At R1--R4 a singleton created by removing"
            " a coordinate remains COMPATIBILITY_NOT_EVALUATED unless it descends from an"
            " already compatible singleton; no projected compatibility is invented."
        ),
        "first_rung_with_an_identified_decision": first_pass,
        "rungs": rungs,
    }, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
