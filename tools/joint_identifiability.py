"""Enforce the frozen joint-identifiability protocol on a verdict record.

The protocol is prose (`docs/paper-a/joint-identifiability-protocol-v1.md`); this is the part
of it a machine can refuse. A verdict that violates a rule is rejected here rather than
carried into a table, because the rules that matter most are the ones a tired adjudicator
would round off: calling a single observable candidate IDENTIFIED without a closed universe,
folding "no admissible combination" into "insufficient evidence", or -- the one this whole
re-adjudication exists to stop -- picking the candidate whose value matches the paper.

    python tools/joint_identifiability.py --verdicts PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs" / "paper-a"
PROTOCOL = DOCS / "joint-identifiability-protocol-v2.md"

COMPONENTS = ("release_set", "run_output_set", "evaluator_and_configuration",
              "task_universe", "aggregation_rule")
BINDING_STATES = ("BOUND", "MULTIPLE", "UNBOUND")
EVALUATOR_NOT_APPLICABLE = ("EMPTY_PATCH_RATE", "STUCK_LOOP_RATE", "MEAN_API_COST")
STATES = ("IDENTIFIED", "OPEN_UNIVERSE_SINGLETON", "AMBIGUOUS",
          "NO_ADMISSIBLE_TUPLE", "UNIDENTIFIED", "COMPATIBILITY_NOT_EVALUATED")
CLOSURE_GROUNDS = ("AUTHORITATIVE_MANIFEST", "IMMUTABLE_INDEX", "EXHAUSTIVE_RETRIEVED_CLOSURE")
DIAGNOSES = ("EVIDENCE_CONTRADICTS", "CANDIDATE_UNIVERSE_MISSPECIFIED",
             "COMPATIBILITY_RULE_MISSPECIFIED", "UNRESOLVED")
# Section 3. Evidence that names the reported value as the reason a candidate was chosen is
# reverse-inference from the result, and is refused whatever verdict it supports.
RESULT_MATCHING_MARKERS = ("matches_reported", "closest_to_reported", "reproduces_reported",
                           "selected_by_score", "recomputation")


class ProtocolViolation(Exception):
    """A verdict that the frozen protocol does not permit."""


def protocol_digest() -> str:
    return hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()


def check(verdict: dict) -> None:
    """Raise unless this verdict is one the protocol allows. Returns nothing on success."""
    where = verdict.get("decision_id", "<no decision_id>")

    state = verdict.get("state")
    if state not in STATES:
        raise ProtocolViolation(f"{where}: state {state!r} is not one of {STATES}")

    components = verdict.get("components") or {}
    missing = [c for c in COMPONENTS if c not in components]
    if missing:
        raise ProtocolViolation(f"{where}: components not recorded: {missing}")

    for name, component in components.items():
        if component.get("binding") not in BINDING_STATES:
            raise ProtocolViolation(
                f"{where}: component {name} binding must be one of {BINDING_STATES}")
        for marker in RESULT_MATCHING_MARKERS:
            if marker in json.dumps(component).lower():
                raise ProtocolViolation(
                    f"{where}: component {name} cites {marker!r}; selecting a candidate by"
                    " agreement with the reported number is prohibited (protocol §3)")
        candidates = component.get("candidates", [])
        sentinels = [candidate for candidate in candidates
                     if candidate.startswith("NOT_APPLICABLE:")]
        expected_sentinel = f"NOT_APPLICABLE:{verdict.get('outcome_profile')}"
        if (name == "evaluator_and_configuration"
                and verdict.get("outcome_profile") in EVALUATOR_NOT_APPLICABLE
                and candidates != [expected_sentinel]):
            raise ProtocolViolation(f"{where}: direct outcome requires {expected_sentinel}")
        if sentinels and (name != "evaluator_and_configuration"
                          or verdict.get("outcome_profile") not in EVALUATOR_NOT_APPLICABLE
                          or candidates != [expected_sentinel]):
            raise ProtocolViolation(f"{where}: NOT_APPLICABLE candidate is invalid for {name}")

    enumerable = {c: bool(components[c].get("candidates")) for c in COMPONENTS}
    admissible = verdict.get("admissible_tuples")

    if state == "UNIDENTIFIED":
        if all(enumerable.values()):
            raise ProtocolViolation(
                f"{where}: UNIDENTIFIED requires at least one component with no enumerable"
                " candidate set; every component here has candidates."
                " If no combination is admissible the state is NO_ADMISSIBLE_TUPLE.")
        if any(verdict.get(name) is not None
               for name in ("admissible_tuples", "unknown_tuples", "unevaluated_tuples")):
            raise ProtocolViolation(
                f"{where}: tuple counts must be null when compatibility has no complete tuple")
        return

    if not all(enumerable.values()):
        raise ProtocolViolation(
            f"{where}: state {state} claims more than enumerability provides;"
            f" components without candidates: {[c for c, ok in enumerable.items() if not ok]}")

    if state == "COMPATIBILITY_NOT_EVALUATED":
        # This state also covers a filter that ran but could not decide every tuple. In both
        # cases the final admissible count remains unknown.
        applied = verdict.get("compatibility_constraints_applied")
        unknown = verdict.get("unknown_tuples")
        unevaluated = verdict.get("unevaluated_tuples")
        if applied:
            if any(not isinstance(n, int) or n < 0
                   for n in (admissible, unknown, unevaluated)):
                raise ProtocolViolation(
                    f"{where}: evaluated tuple counts must be non-negative integers")
        elif (admissible is not None or unknown is not None
              or not isinstance(unevaluated, int) or unevaluated < 1):
            raise ProtocolViolation(
                f"{where}: unrun compatibility requires null admissible/unknown counts"
                " and a positive unevaluated count")
        if applied and not (unknown or unevaluated):
            raise ProtocolViolation(
                f"{where}: COMPATIBILITY_NOT_EVALUATED with no UNKNOWN or unevaluated tuples")
        return

    if not isinstance(admissible, int) or admissible < 0:
        raise ProtocolViolation(f"{where}: admissible_tuples must be a non-negative integer")
    unknown = verdict.get("unknown_tuples", 0)
    unevaluated = verdict.get("unevaluated_tuples", 0)
    if any(not isinstance(n, int) or n < 0 for n in (unknown, unevaluated)):
        raise ProtocolViolation(
            f"{where}: unknown_tuples and unevaluated_tuples must be non-negative integers")

    if (not verdict.get("compatibility_constraints_applied") or unknown or unevaluated):
        raise ProtocolViolation(
            f"{where}: {state} requires complete compatibility evaluation")

    if state == "NO_ADMISSIBLE_TUPLE":
        if admissible != 0:
            raise ProtocolViolation(f"{where}: NO_ADMISSIBLE_TUPLE with {admissible} admissible tuples")
        diagnosis = verdict.get("diagnosis") or []
        if not diagnosis or any(d not in DIAGNOSES for d in diagnosis):
            raise ProtocolViolation(f"{where}: diagnosis must be a non-empty subset of {DIAGNOSES}")
        return

    if state == "AMBIGUOUS":
        if admissible < 2:
            raise ProtocolViolation(f"{where}: AMBIGUOUS with {admissible} admissible tuples")
        if "implied_value_range" not in verdict:
            raise ProtocolViolation(f"{where}: AMBIGUOUS must record implied_value_range")
        return

    # IDENTIFIED and OPEN_UNIVERSE_SINGLETON both require exactly one admissible tuple.
    if admissible != 1:
        raise ProtocolViolation(f"{where}: {state} with {admissible} admissible tuples")

    closure = verdict.get("universe_closure")
    if state == "IDENTIFIED":
        if closure not in CLOSURE_GROUNDS:
            raise ProtocolViolation(
                f"{where}: IDENTIFIED requires a closure ground from {CLOSURE_GROUNDS};"
                f" got {closure!r}. One observable candidate without a closed universe is"
                " OPEN_UNIVERSE_SINGLETON (protocol §4.1).")
    elif closure in CLOSURE_GROUNDS:
        raise ProtocolViolation(
            f"{where}: OPEN_UNIVERSE_SINGLETON records closure ground {closure!r};"
            " a closed universe with one admissible tuple is IDENTIFIED")


def aggregate(verdicts: list[dict], field: str = "study_id") -> dict:
    """Protocol §5: a group is identified only if every audited decision is IDENTIFIED."""
    studies: dict[str, list[str]] = {}
    for verdict in verdicts:
        studies.setdefault(verdict[field], []).append(verdict["state"])
    out = {}
    for study, states in studies.items():
        if all(s == "IDENTIFIED" for s in states):
            out[study] = "IDENTIFIED"
        elif any(s in ("UNIDENTIFIED", "AMBIGUOUS", "NO_ADMISSIBLE_TUPLE",
                       "OPEN_UNIVERSE_SINGLETON") for s in states):
            out[study] = "NOT_IDENTIFIED"
        else:
            # What is left is COMPATIBILITY_NOT_EVALUATED, alone or beside IDENTIFIED. A
            # determinate negative would have matched above; not knowing is not a negative,
            # so the study gets no verdict rather than a convenient one.
            out[study] = "UNRESOLVED"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdicts", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = json.loads(args.verdicts.read_text())
    pinned = payload.get("protocol_sha256")
    live = protocol_digest()
    if pinned != live:
        print(f"protocol digest mismatch: verdicts pin {pinned}, file is {live}")
        return 2

    verdicts = payload["verdicts"]
    for verdict in verdicts:
        check(verdict)
    counts: dict[str, int] = {}
    for verdict in verdicts:
        counts[verdict["state"]] = counts.get(verdict["state"], 0) + 1
    print(f"{len(verdicts)} verdicts admitted under protocol {live[:16]}")
    print("decision states:", counts)
    print("study level:    ", aggregate(verdicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
